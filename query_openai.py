import os
from openai import OpenAI

token = os.getenv("GITHUB_TOKEN_API")

endpoint = "https://models.github.ai/inference"
model = "openai/gpt-5-mini"

client = OpenAI(
    base_url=endpoint,
    api_key=token
)

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "system",
            "content": "You are a skilled Arabic poet, expert in Mahmoud Darwich style."
        },
        {
            "role": "user",
            "content": "Écris un poème court en arabe classique, dans le style de Mahmoud Darwich, sur mon stage en NLP et IA, décrivant les difficultés que je surmonte avec courage en tant qu’étudiant ingénieur, avec des images puissantes et un langage riche."  
        }
    ]
)

print(response.choices[0].message.content)
