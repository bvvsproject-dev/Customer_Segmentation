document.addEventListener('DOMContentLoaded', async () => {
    // Only run if canvas exists
    if (!document.getElementById('scatterChart')) return;

    try {
        const response = await fetch('/api/data');
        const dataStatus = await response.json();
        
        if (dataStatus.status !== 'success') {
            console.error('Failed to load data', dataStatus.message);
            return;
        }

        const data = dataStatus.data;
        
        // Populate stats
        if (document.getElementById('stat-total')) {
            document.getElementById('stat-total').textContent = data.total_customers;
            document.getElementById('stat-income').textContent = data.avg_income.toFixed(1);
            document.getElementById('stat-age').textContent = data.avg_age.toFixed(1);
        }

        // Update Chart defaults based on theme
        const updateChartTheme = () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            Chart.defaults.color = isDark ? '#94a3b8' : '#6B7280';
            Chart.defaults.borderColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
            for (const id in Chart.instances) {
                Chart.instances[id].update();
            }
        };
        
        // Initial setup
        Chart.defaults.font.family = "'Inter', 'Poppins', sans-serif";
        updateChartTheme();

        // Listen for theme toggle changes
        window.addEventListener('themeChanged', updateChartTheme);
        
        // Common animation settings
        const commonAnimations = {
            tension: {
                duration: 1000,
                easing: 'linear',
                from: 1,
                to: 0,
                loop: false
            }
        };

        const clusterColors = [
            '#4F8CFF', '#22C55E', '#F59E0B', '#EF4444', 
            '#7F7FD5', '#60A5FA', '#F472B6', '#10B981'
        ];

        // 1. Scatter Plot (Chart.js 2D)
        const scatterCtx = document.getElementById('scatterChart');
        if (scatterCtx && scatterCtx.tagName === 'CANVAS') {
            const datasets = [];
            const numClusters = Math.max(...data.scatter_points.map(p => p.cluster)) + 1;
            
            for (let i = 0; i < numClusters; i++) {
                const clusterPoints = data.scatter_points.filter(p => p.cluster === i);
                if (clusterPoints.length > 0) {
                    datasets.push({
                        label: `Cluster ${i}`,
                        data: clusterPoints.map(p => ({x: p.x, y: p.y, age: p.age})),
                        backgroundColor: clusterColors[i % clusterColors.length],
                        pointRadius: 6,
                        pointHoverRadius: 9,
                        borderWidth: 2,
                        borderColor: 'rgba(255,255,255,0.8)'
                    });
                }
            }

            new Chart(scatterCtx.getContext('2d'), {
                type: 'scatter',
                data: { datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1500,
                        easing: 'easeOutQuart'
                    },
                    scales: {
                        x: {
                            title: { display: true, text: 'Annual Income (k$)' },
                            grid: { drawBorder: false }
                        },
                        y: {
                            title: { display: true, text: 'Spending Score (1-100)' },
                            grid: { drawBorder: false }
                        }
                    },
                    plugins: {
                        zoom: {
                            zoom: {
                                wheel: { enabled: true },
                                pinch: { enabled: true },
                                mode: 'xy'
                            },
                            pan: {
                                enabled: true,
                                mode: 'xy'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(31, 41, 55, 0.9)',
                            padding: 12,
                            cornerRadius: 8,
                            callbacks: {
                                label: (ctx) => `Income: ${ctx.parsed.x}k, Score: ${ctx.parsed.y}`
                            }
                        },
                        legend: {
                            labels: { usePointStyle: true, boxWidth: 8 }
                        }
                    }
                }
            });
        }

        // 2. Elbow Line Chart
        if (data.wcss && data.k_range) {
            const elbowCtx = document.getElementById('elbowChart').getContext('2d');
            
            // Create gradient fill
            const gradient = elbowCtx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(79, 140, 255, 0.4)'); // #4F8CFF with opacity 0.4
            gradient.addColorStop(1, 'rgba(79, 140, 255, 0.0)');

            new Chart(elbowCtx, {
                type: 'line',
                data: {
                    labels: data.k_range,
                    datasets: [{
                        label: 'WCSS',
                        data: data.wcss,
                        borderColor: '#4F8CFF',
                        backgroundColor: gradient,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#4F8CFF',
                        pointHoverBackgroundColor: '#4F8CFF',
                        pointHoverBorderColor: '#fff',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1500,
                        easing: 'easeOutQuart'
                    },
                    scales: {
                        x: { title: { display: true, text: 'Number of Clusters (K)' }, grid: { display: false } },
                        y: { title: { display: true, text: 'WCSS' }, grid: { borderDash: [5, 5] } }
                    },
                    plugins: {
                        tooltip: { backgroundColor: 'rgba(31, 41, 55, 0.9)', padding: 10, cornerRadius: 8 }
                    }
                }
            });
        }

        // 3. Silhouette Bar Chart
        if (data.silhouette_scores && data.k_range) {
            const silCtx = document.getElementById('silhouetteChart').getContext('2d');
            
            // Highlight optimal K
            const optimal_k = data.optimal_k;
            const bgColors = data.k_range.map(k => 
                k === optimal_k ? '#4F8CFF' : 'rgba(127, 127, 213, 0.4)'
            );
            const hoverColors = data.k_range.map(k => 
                k === optimal_k ? '#3a72d6' : 'rgba(127, 127, 213, 0.6)'
            );
            
            new Chart(silCtx, {
                type: 'bar',
                data: {
                    labels: data.k_range,
                    datasets: [{
                        label: 'Silhouette Score',
                        data: data.silhouette_scores,
                        backgroundColor: bgColors,
                        hoverBackgroundColor: hoverColors,
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1500,
                        easing: 'easeOutQuart'
                    },
                    scales: {
                        x: { title: { display: true, text: 'Number of Clusters (K)' }, grid: { display: false } },
                        y: { title: { display: true, text: 'Score' }, grid: { borderDash: [5, 5] } }
                    },
                    plugins: {
                        tooltip: { backgroundColor: 'rgba(31, 41, 55, 0.9)', padding: 10, cornerRadius: 8 }
                    }
                }
            });
        }

    } catch (error) {
        console.error("Error drawing charts:", error);
    }
});
