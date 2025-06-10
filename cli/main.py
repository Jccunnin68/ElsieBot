import click
import requests
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

console = Console()

class ElsieCLI:
    def __init__(self):
        self.ai_agent_url = "http://localhost:8000"
        self.console = Console()

    def process_message(self, message: str, context: dict = None) -> dict:
        """Send message to AI agent for processing"""
        try:
            response = requests.post(
                f"{self.ai_agent_url}/process",
                json={"content": message, "context": context or {}}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]Error communicating with AI agent: {str(e)}[/red]")
            return {"status": "error", "response": str(e)}

    def display_response(self, response: dict):
        """Display the AI agent's response in a formatted way"""
        if response["status"] == "success":
            self.console.print(Panel(
                Markdown(response["response"]),
                title="Elsie's Response",
                border_style="green"
            ))
        else:
            self.console.print(Panel(
                f"Error: {response['response']}",
                title="Error",
                border_style="red"
            ))

@click.group()
def cli():
    """Elsie - Your AI Assistant"""
    pass

@cli.command()
def chat():
    """Start an interactive chat session with Elsie"""
    elsie = ElsieCLI()
    console.print(Panel(
        "Welcome to Elsie! Type 'exit' to quit.",
        title="Elsie CLI",
        border_style="blue"
    ))

    context = {}
    while True:
        try:
            user_input = click.prompt("\nYou", type=str)
            if user_input.lower() in ['exit', 'quit', 'bye']:
                console.print("[yellow]Goodbye![/yellow]")
                break

            response = elsie.process_message(user_input, context)
            elsie.display_response(response)

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {str(e)}[/red]")

@cli.command()
@click.argument('message')
def ask(message):
    """Ask Elsie a single question"""
    elsie = ElsieCLI()
    response = elsie.process_message(message)
    elsie.display_response(response)

if __name__ == '__main__':
    cli() 