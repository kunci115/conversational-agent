import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from payment.process import send_information_order
import json

# Load environment variables
load_dotenv()

# Azure OpenAI configuration
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
api_key = os.environ["OPENAI_API_KEY"]
deployment = os.environ["CHAT_COMPLETIONS_DEPLOYMENT_NAME"]
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

# Initialize client
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version="2024-02-01",
)
PROMPT_FILE_NAME = os.environ["PROMPT_FILE_NAME"]
# Read system prompt from file
with open('prompt/' + PROMPT_FILE_NAME, "r") as file:
    system_prompt = file.read()

# Initialize message history with system prompt
message_history = [
    {"role": "system", "content": system_prompt},
]

tools = [
    {
        "type": "function",
        "function": {
            "name": "send_information_order",
            "description": "Report Purchase send to email",
            "parameters": {
                "type": "object",
                "properties": {
                    "total_price": {
                        "type": "integer",
                        "description": "total price of pizza order",
                    },
                    "product_list": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "quantity": {
                            "type": "integer",
                        },
                        "description": "items that customer already choose to order",
                    },
                    "email": {
                        "type": "string",
                        "description": "token number of payment from customer, to be check by system true money",
                    }
                },
                "required": ["total_price", "product_list", "token_payment"],
            }
        }
    }
]
available_functions = {
    "send_information_order": send_information_order
}

def get_user_input():
    return input("User: ")

def get_response_from_openai(messages, available_functions):
    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    response_message = response.choices[0].message
    response_tool_calls = response_message.tool_calls
    if response_tool_calls == None:
        return response_message.content
    for tool_call in response_tool_calls:
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        function_name = tool_call.function.name
        # verify function exists
        if function_name not in available_functions:
            return "Function " + function_name + " does not exist"
        function_to_call = available_functions[function_name]
        
        function_args = json.loads(tool_call.function.arguments)
        function_response = function_to_call(**function_args)
        messages.append({
            "role": "assistant",
            "content": f"Function {function_name} was called with arguments {json.dumps(function_args)} and returned {json.dumps(function_response)}"
        })
        # verify function has correct number of arguments
        print("Output of function call:")
        print(function_response)
        print()
        messages.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response
        second_response = client.chat.completions.create(
            model=deployment,
            messages=messages,
        )  # get a new response from the model where it can see the function response
        return second_response
    return 

# Main loop
while True:
    user_message = get_user_input()
    message_history.append({"role": "user", "content": user_message})
    
    response = get_response_from_openai(message_history, available_functions)
    
    print(f"Assistant: {response}")
    message_history.append({"role": "assistant", "content": response})
    
    # Optional: Save history to a file for persistence
    with open("chat_history.txt", "a") as file:
        file.write(f"User: {user_message}\n")
        file.write(f"Assistant: {response}\n")
