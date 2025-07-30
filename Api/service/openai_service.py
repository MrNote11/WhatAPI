from openai import OpenAI
import shelve
from dotenv import load_dotenv
import os
import time
import logging
load_dotenv()



EXA = os.getenv("EXA")
from exa_py import Exa

EXA_API_KEY = os.getenv("EXA")  # this should be your actual API key
exa = Exa(api_key=EXA_API_KEY)  # create an instance of the client




# --------------------------------------------------------------

def run_exa_search(message_body):
    logging.info(f"Running Exa search for query: {message_body}")

    # You can adjust filters, limit, etc., as needed
    results = exa.search_and_contents(
        message_body,
        text=True,
        num_results=3
    )

    # Combine top 3 results into a readable response
    if not results.results:
        return "Sorry, I couldn't find any reliable information. Please contact the host."

    response_parts = []
    for i, result in enumerate(results.results):
        content = result.document.get("text", "")
        title = result.document.get("title", "")
        link = result.document.get("url", "")
        response_parts.append(f"{i+1}. *{title}*\n{content[:250]}...\n🔗 {link}")

    return "\n\n".join(response_parts)

def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, query):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = query

# -- Response generation using Exa.ai ---------------------------------------

def generate_response(message_body, wa_id, name):
    """
    Instead of using OpenAI Assistants, we query Exa for search results
    and build a text response.
    """
    previous_query = check_if_thread_exists(wa_id)

    # You can enhance this by combining old + new queries
    logging.info(f"Generating Exa.ai response for {name} ({wa_id})")

    # Run search via Exa
    results = exa.search_and_contents(message_body, text=True)

    # Save the message body as the current thread for that wa_id
    store_thread(wa_id, message_body)

    # Build a human-friendly response from top result
    if results and results.results:
        top = results.results[0]
        title = top.title
        content = top.text[:500]  # limit to 500 chars
        url = top.url
        return f"🧠 Here's something I found:\n\n🔍 *{title}*\n\n{content}\n\n🔗 {url}"
    else:
        return "🤷‍♂️ I couldn't find any reliable info on that. You can ask something else."

 
