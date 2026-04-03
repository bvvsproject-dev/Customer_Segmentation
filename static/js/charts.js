let scatterChartInstance = null;
let elbowChartInstance = null;
let silChartInstance = null;
let currentFilteredPoints = [];

const clusterColors = [
    '#4F8CFF', '#22C55E', '#F59E0B', '#EF4444', 
    '#7F7FD5', '#60A5FA', '#F472B6', '#10B981',
    '#9CA3AF', '#D946EF'
];

async function fetchAndRenderDashboard() {
    if (!document.getElementById('scatterChart')) return;

    const modelType = document.getElementById('modelSelect') ? document.getElementById('modelSelect').value : 'kmeans';
    const maxAge = document.getElementById('ageFilter') ? parseInt(document.getElementById('ageFilter').value) : 100;
    const maxIncome = document.getElementById('incomeFilter') ? parseInt(document.getElementById('incomeFilter').value) : 200;

    try {
        const response = await fetch(`/api/data?model_type=${modelType}`);
        const dataStatus = await response.json();
        
        if (dataStatus.status !== 'success') {
            console.error('Failed to load data', dataStatus.message);
            return;
        }

        const rawData = dataStatus.data;
        
        // Apply Filters
        const filteredPoints = rawData.scatter_points.filter(p => p.age <= maxAge && p.x <= maxIncome);
        currentFilteredPoints = filteredPoints;
        
        // Populate stats
        if (document.getElementById('stat-total')) {
            document.getElementById('stat-total').textContent = filteredPoints.length;
            const avgInc = filteredPoints.length > 0 ? (filteredPoints.reduce((sum, p) => sum + p.x, 0) / filteredPoints.length) : 0;
            const avgAg = filteredPoints.length > 0 ? (filteredPoints.reduce((sum, p) => sum + p.age, 0) / filteredPoints.length) : 0;
            
            document.getElementById('stat-income').textContent = avgInc.toFixed(1);
            document.getElementById('stat-age').textContent = avgAg.toFixed(1);
        }

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        Chart.defaults.color = isDark ? '#94a3b8' : '#6B7280';
        Chart.defaults.borderColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
        Chart.defaults.font.family = "'Inter', 'Poppins', sans-serif";

        renderScatterChart(filteredPoints);
        
        // Fetch Elbow and Silhouette graphs exclusively
        if (modelType === 'kmeans' || modelType === 'hierarchical') {
            fetch(`/api/elbow-data`)
                .then(res => res.json())
                .then(d => {
                    if (d.k_range && d.wcss) renderElbowChart(d.k_range, d.wcss);
                })
                .catch(err => console.error(err));
                
            const silSpinner = document.getElementById('silSpinner');
            if (silSpinner) silSpinner.style.display = 'block';
            
            fetch(`/silhouette-data`)
                .then(res => res.json())
                .then(d => {
                    if (silSpinner) silSpinner.style.display = 'none';
                    if (d.k_values && d.scores && d.k_values.length > 0) {
                        renderSilhouetteChart(d.k_values, d.scores);
                    } else {
                        console.error('No silhouette data returned');
                    }
                })
                .catch(err => {
                    if (silSpinner) silSpinner.style.display = 'none';
                    console.error('Error fetching silhouette data:', err);
                });
        } else {
            // Clear or hide charts for DBSCAN, as they don't apply
            if (elbowChartInstance) elbowChartInstance.destroy();
            if (silChartInstance) silChartInstance.destroy();
        }

    } catch (error) {
        console.error("Error drawing charts:", error);
    }
}


function renderScatterChart(points) {
    const scatterCtx = document.getElementById('scatterChart');
    if (!scatterCtx) return;

    if (scatterChartInstance) {
        scatterChartInstance.destroy();
    }

    const datasets = [];
    // Handle noise cluster (-1) in DBSCAN safely
    const minCluster = Math.min(...points.map(p => p.cluster));
    const maxCluster = Math.max(...points.map(p => p.cluster));
    
    for (let i = minCluster; i <= maxCluster; i++) {
        const clusterPoints = points.filter(p => p.cluster === i);
        if (clusterPoints.length > 0) {
            const isNoise = i === -1;
            datasets.push({
                label: isNoise ? `Noise / Outliers` : `Cluster ${i}`,
                data: clusterPoints.map(p => ({x: p.x, y: p.y, age: p.age, gender: p.gender})),
                backgroundColor: isNoise ? '#6B7280' : clusterColors[i % clusterColors.length],
                pointRadius: isNoise ? 4 : 6,
                pointHoverRadius: 9,
                borderWidth: 2,
                borderColor: 'rgba(255,255,255,0.8)'
            });
        }
    }

    scatterChartInstance = new Chart(scatterCtx.getContext('2d'), {
        type: 'scatter',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 800, easing: 'easeOutQuart' },
            scales: {
                x: { title: { display: true, text: 'Annual Income (k$)' }, grid: { drawBorder: false } },
                y: { title: { display: true, text: 'Spending Score (1-100)' }, grid: { drawBorder: false } }
            },
            plugins: {
                zoom: {
                    zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'xy' },
                    pan: { enabled: true, mode: 'xy' }
                },
                tooltip: {
                    backgroundColor: 'rgba(31, 41, 55, 0.9)',
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(ctx) {
                            const pt = ctx.raw;
                            return `Age: ${pt.age} | Gender: ${pt.gender} | Income: $${pt.x}k | Score: ${pt.y}`;
                        }
                    }
                },
                legend: {
                    labels: { usePointStyle: true, boxWidth: 8 },
                    onClick: function(e, legendItem, legend) {
                        const index = legendItem.datasetIndex;
                        const ci = legend.chart;
                        if (ci.isDatasetVisible(index)) {
                            ci.hide(index);
                            legendItem.hidden = true;
                        } else {
                            ci.show(index);
                            legendItem.hidden = false;
                        }
                    }
                }
            }
        }
    });
}

function renderElbowChart(k_range, wcss) {
    const elbowCtx = document.getElementById('elbowChart');
    if (!elbowCtx) return;
    
    if (elbowChartInstance) {
        elbowChartInstance.destroy();
    }

    const gradient = elbowCtx.getContext('2d').createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(79, 140, 255, 0.4)');
    gradient.addColorStop(1, 'rgba(79, 140, 255, 0.0)');

    elbowChartInstance = new Chart(elbowCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: k_range,
            datasets: [{
                label: 'WCSS',
                data: wcss,
                borderColor: '#4F8CFF',
                backgroundColor: gradient,
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#4F8CFF',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Number of Clusters (K)' }, grid: { display: false } },
                y: { title: { display: true, text: 'WCSS' }, grid: { borderDash: [5, 5] } }
            }
        }
    });
}

function renderSilhouetteChart(k_values, scores) {
    const silCtx = document.getElementById('silhouetteChart');
    if (!silCtx) return;

    if (silChartInstance) {
        silChartInstance.destroy();
    }

    // Highlight best K (highest score)
    const maxScore = Math.max(...scores);
    const bestKIndex = scores.indexOf(maxScore);
    const bestK = k_values[bestKIndex];

    const bgColors = k_values.map(k => k === bestK ? '#4F8CFF' : 'rgba(127, 127, 213, 0.4)');
    const hoverColors = k_values.map(k => k === bestK ? '#3a72d6' : 'rgba(127, 127, 213, 0.6)');

    silChartInstance = new Chart(silCtx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: k_values,
            datasets: [{
                label: 'Silhouette Score',
                data: scores,
                backgroundColor: bgColors,
                hoverBackgroundColor: hoverColors,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            animation: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(3);
                            }
                            if (context.dataIndex === bestKIndex) {
                                label += ' (Best K) - High score means better clustering';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: { title: { display: true, text: 'Number of Clusters (K)' }, grid: { display: false } },
                y: { title: { display: true, text: 'Score' }, grid: { borderDash: [5, 5] } }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchAndRenderDashboard();

    // Event Listeners for controls
    const modelSelect = document.getElementById('modelSelect');
    const ageFilter = document.getElementById('ageFilter');
    const incomeFilter = document.getElementById('incomeFilter');
    
    if (modelSelect) {
        modelSelect.addEventListener('change', fetchAndRenderDashboard);
    }
    
    if (ageFilter) {
        ageFilter.addEventListener('input', (e) => {
            document.getElementById('ageVal').textContent = e.target.value;
            fetchAndRenderDashboard();
        });
    }
    
    if (incomeFilter) {
        incomeFilter.addEventListener('input', (e) => {
            document.getElementById('incomeVal').textContent = e.target.value;
            fetchAndRenderDashboard();
        });
    }

    window.addEventListener('themeChanged', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        Chart.defaults.color = isDark ? '#94a3b8' : '#6B7280';
        Chart.defaults.borderColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
        if (scatterChartInstance) scatterChartInstance.update();
        if (elbowChartInstance) elbowChartInstance.update();
        if (silChartInstance) silChartInstance.update();
    });


    const exportPdfBtn = document.getElementById('exportPdfBtn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', async () => {
            exportPdfBtn.disabled = true;
            exportPdfBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
            
            try {
                // Gather stats
                const statTotal = document.getElementById('stat-total') ? document.getElementById('stat-total').innerText : 0;
                const statInc = document.getElementById('stat-income') ? document.getElementById('stat-income').innerText : 0;
                const statAge = document.getElementById('stat-age') ? document.getElementById('stat-age').innerText : 0;
                
                // Get Charts as base64 (force light background for PDF)
                // Temporarily inject white background if transparent
                const getChartBase64 = (chartInst) => {
                    if (!chartInst) return null;
                    return chartInst.toBase64Image('image/jpeg', 1.0);
                };

                const scatterB64 = getChartBase64(scatterChartInstance);
                const elbowB64 = getChartBase64(elbowChartInstance);
                const silB64 = getChartBase64(silChartInstance);
                
                const payload = {
                    stats: { total: statTotal, income: statInc, age: statAge },
                    charts: { scatter: scatterB64, elbow: elbowB64, silhouette: silB64 },
                    insights: []
                };
                
                const response = await fetch('/api/export/pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) throw new Error('Network response was not ok');
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'Customer_Insights_Report.pdf';
                document.body.appendChild(a);
                a.click();
                a.remove();
                
            } catch (err) {
                console.error("PDF Export Error:", err);
                alert("Failed to export complete PDF: " + err.message);
            } finally {
                exportPdfBtn.disabled = false;
                exportPdfBtn.innerHTML = '<i class="fas fa-file-pdf"></i> Export PDF';
            }
        });
    }

    const exportCsvBtn = document.getElementById('exportCsvBtn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => {
            if (!currentFilteredPoints || currentFilteredPoints.length === 0) {
                alert("No data to export.");
                return;
            }
            
            let csvContent = "data:text/csv;charset=utf-8,";
            csvContent += "Cluster,Age,Gender,Income_k$,Spending_Score\n";
            
            currentFilteredPoints.forEach(p => {
                const row = `${p.cluster},${p.age},${p.gender},${p.x},${p.y}`;
                csvContent += row + "\n";
            });
            
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "customer_segments_export.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }
});
