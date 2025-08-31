# 用於將非結構化資料轉換成JSON格式，以便後續關卡需要JSON輸入時使用
import json
from typing import Dict, Any
from fastmcp import FastMCP

mcp = FastMCP("NL to JSON Converter")

@mcp.tool()
def structured_data_converting(generated_content):
    """
    Converts a natural language prompt into a structured JSON object based on a provided API schema.
    """
    try:
        structured_data = json.loads(generated_content)
        return structured_data

    except Exception as e:
        print(f"An error occurred during conversion: {e}")
        return {"error": str(e), "message": "Failed to generate valid structured output."}

if __name__ == "__main__":
    print("--- Starting FastMCP Server: NL to JSON Converter ---")
    print("This server exposes the 'convert_to_structured_input' tool.")
    print("Press Ctrl+C to stop the server.")
    mcp.run()
