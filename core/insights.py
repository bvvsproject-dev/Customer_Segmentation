import google.generativeai as genai
import os

def explain_segment(label, cluster_stats):
    """
    Calls the Gemini API to provide a targeted business explanation of a specific customer segment.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        You are an expert marketing analyst. 
        I have a customer segment labeled '{label}'. 
        Here are the average stats for this cluster: {cluster_stats}.
        
        Please provide:
        1. A 2-sentence summary explaining who these customers are.
        2. Two specific, highly actionable marketing bullet points (no fluff).
        Format your response using html tags like <b>, <i>, <br> only. No markdown ## or **.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"<i>Unable to generate AI insights at this time: {str(e)}</i>"

def suggest_strategy(label, cluster_stats):
    """
    Calls the Gemini API to suggest a high-level strategic approach.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        You are a Chief Revenue Officer. 
        For the customer segment '{label}' (Stats: {cluster_stats}), recommend exactly ONE primary business strategy 
        to maximize their Lifetime Value (LTV). Be concise and authoritative. 
        Format your response using basic HTML only.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"<i>Strategy generation failed: {str(e)}</i>"
