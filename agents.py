from google import genai 

client = genai.Client(api_key = '')

response = client.models.generate_content(
    model = "gemini-3-flash-preview",
    contents = "What is IMDB?"

)

print(response.text)
