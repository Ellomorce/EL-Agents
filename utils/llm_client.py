#%%
import os
import ollama
import yaml
from utils import response_schema
from dotenv import load_dotenv
from google import genai
from google.genai import types

class GeminiClient:

    def __init__(self):
        """
        Documentation: https://ai.google.dev/gemini-api/docs?hl=zh-tw
        """
        load_dotenv(".env")
        self.config_path = "llm_config.yaml"
        self.prompt_path = "prompts.yaml"
        self.client = genai.Client(api_key=os.getenv("GCP_API_KEY"))

    def select_config(self, config_key):
        with open(self.config_path, 'r', encoding="utf-8") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)[config_key]
        return config
    
    def select_prompt(self, prompt_key):
        with open(self.prompt_path, 'r', encoding="utf-8") as file:
            system_prompt = yaml.load(file, Loader=yaml.FullLoader)[prompt_key]
        return system_prompt
    
    def select_schema(schema_name):
        schema_class = getattr(response_schema, schema_name)
        schema_dict = schema_class.model_json_schema()
        result_schema = {
            "type": schema_dict["type"],
            "properties": schema_dict["properties"],
            "required": schema_dict["required"]
        }
        return result_schema
    
    def select_tools(self, tool_name):
        match tool_name:
            case "exe_code":
                tool_option = types.Tool(code_execution=types.ToolCodeExecution)
            case "get_urlpage":
                tool_option = types.Tool(url_context=types.UrlContext)
            case "web_search":
                tool_option = types.Tool(google_search=types.GoogleSearch)
            case _:
                tool_option = None
        return tool_option
    
    def generate_text(self, model:str, config_data:dict, system_prompt:str, user_query:str, tool_use:str=None):
        """
        用於單次推論文字生成，模型會進行單次生成
        """
        if tool_use == None:
            tool_options = []
        else:
            tool_options = [tool_use]
        config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=system_prompt,
            temperature=config_data["temperature"],
            top_p=config_data["top_p"],
            max_output_tokens=config_data["max_output_tokens"],
            frequency_penalty=config_data["frequency_penalty"],
            tools=tool_options,
            response_modalities=["TEXT"]
            )
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_query),
                ],
            )]
        try:
            response = self.client.models.generate_content(model=model, contents=contents, config=config)
            errmsg = None
            return errmsg, response
        except Exception as errmsg:
            response = None
            return errmsg, response

    def generate_structured_text(self, model:str, config_data:dict, system_prompt:str, user_query:str, tool_use:str=None, schema_name:str=None):
        """
        用於單次推論結構化文字生成
        進階用法請參考 https://ai.google.dev/gemini-api/docs/structured-output?hl=zh-tw
        """
        # 利用參數字串來動態引入response_schema.py中的class
        try:
            schema_class = getattr(response_schema, schema_name)
        except AttributeError:
            raise ValueError(f"Class '{schema_name}' not found in response_schema.py")
        #
        if tool_use == None:
            tool_options = []
        else:
            tool_options = [tool_use]
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=system_prompt,
            temperature=config_data["temperature"],
            top_p=config_data["top_p"],
            max_output_tokens=config_data["max_output_tokens"],
            frequency_penalty=config_data["frequency_penalty"],
            tools=tool_options,
            response_schema=list[schema_class]
            )
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_query),
                ],
            )]
        try:
            response = self.client.models.generate_content(model=model, contents=contents, config=config)
            errmsg = None
            return errmsg, response
        except Exception as errmsg:
            response = None
            return errmsg, response
        
    def response_filter(self, response):
        response_text = None
        response_code = None
        response_codeoutput = None
        function_call_text = None
        function_response_text = None
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                response_text = part.text
            else:
                pass
            if part.executable_code:
                if part.executable_code is not None:
                    response_code = part.executable_code
                else:
                    pass
            else:
                pass
            if part.code_execution_result:
                if part.code_execution_result is not None:
                    response_codeoutput = part.code_execution_result.output
                else:
                    pass
            else:
                pass
            if part.function_call:
                if part.function_call is not None:
                    function_call_text = part.function_call
                    if part.function_response is not None:
                        function_response_text = part.function_response
                    else:
                        pass
                else:
                    pass
            else:
                pass
        return response_text, response_code, response_codeoutput, function_call_text, function_response_text

class OllamaClient:

    def __init__(self) -> None:
        self.config_path = "llm_config.yaml"
        self.prompt_path = "prompts.yaml"

    def select_config(self, config_key):
        with open(self.config_path, 'r', encoding="utf-8") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)[config_key]
        return config
    
    def select_schema(self, schema_name):
        if schema_name == None:
            return None
        else:
            schema_class = getattr(response_schema, schema_name)
            schema_dict = schema_class.model_json_schema()
            result_schema = {
                "type": schema_dict["type"],
                "properties": schema_dict["properties"],
                "required": schema_dict["required"]
            }
            return result_schema

    def select_prompt(self, prompt_key):
        with open(self.prompt_path, 'r', encoding="utf-8") as file:
            system_prompt = yaml.load(file, Loader=yaml.FullLoader)[prompt_key]
        return system_prompt

    def create_contents(self, system_prompt:str, user_query:str=None):
        messages=[{"role": "system", "content": system_prompt}]
        if user_query == None:
            return messages
        else:
            user_content = {"role": "user", "content": user_query}
            messages.append(user_content)
            return messages
        
    def chat(self, model:str, config_data:dict, messages:list, tool_use:str=None):
        if tool_use == None:
            tool_options = []
        else:
            tool_options = [tool_use]
        config = {
            "temperature": config_data["temperature"],
            "top_p": config_data["top_p"],
            "num_predict": config_data["max_output_tokens"],
            "frequency_penalty": config_data["frequency_penalty"]
        }
        try:
            response = ollama.chat(model=model, messages=messages, tools=tool_options, options=config)
            errmsg = None
            return errmsg, response
        except Exception as errmsg:
                response = None
                return errmsg, response
        
    def sturctured_chat(self, model:str, config_data:dict, messages:list, tool_use:str=None, schema_name:str=None):
        if tool_use == None:
            tool_options = []
        else:
            tool_options = [tool_use]
        schema = self.select_schema(schema_name)
        config = {
            "temperature": config_data["temperature"],
            "top_p": config_data["top_p"],
            "num_predict": config_data["max_output_tokens"],
            "frequency_penalty": config_data["frequency_penalty"]
        }
        try:
            response = ollama.chat(model=model, 
                                   messages=messages, 
                                   tools=tool_options, 
                                   format=schema,
                                   options=config)
            errmsg = None
            return errmsg, response
        except Exception as errmsg:
                response = None
                return errmsg, response
        
class LitellmClient:

    def __init__(self) -> None:
        self.config_path = "llm_config.yaml"
        self.prompt_path = "prompts.yaml"

    def chat():
        pass
#%%
if __name__=='__main__':
    # llm = GeminiClient()
    # config_data = llm.select_config(config_key="precise")
    # system_prompt = llm.select_prompt(prompt_key="test.system")
    # print(system_prompt)
    # model = "gemini-2.0-flash"
    # user_query = "約翰是個可靠的工程師"
    # errmsg, result = llm.generate_text(model, config_data, system_prompt, user_query)
    # print(errmsg)
    # print(result)
    client = OllamaClient()
    model = "gemma3n:e4b"
    config_data = client.select_config(config_key="precise")
    system_prompt = client.select_prompt(prompt_key="test.system")
    user_query = "約翰是個可靠的工程師"
    messages = client.create_contents(system_prompt=system_prompt, user_query=user_query)
    errmsg, response = client.chat(model, config_data, messages)
    print(errmsg)
    print("------")
    # print(response)
    print(response['message']['content'])
#%%