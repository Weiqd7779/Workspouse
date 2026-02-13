import os
import sys
from typing import Optional, AsyncGenerator
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

load_dotenv()

class ChatClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.getenv("BASE_URL")
        self.api_key = api_key or os.getenv("API_KEY")
        self.model = model or os.getenv("MODEL", "model")

        if not self.base_url:
            raise ValueError("BASE_URL is not set in environment or arguments.")

        self.llm = ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "dummy", # Some compatible servers need a dummy key
            model=self.model,
            streaming=True,
            temperature=0.7 # Default, can be overridden per run
        )

    def chat_stream(self, messages: list[BaseMessage], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Streams the response from the LLM."""
        # Update temperature for this call if needed (LangChain object might need re-instantiation or config update)
        # For simplicity, we'll just set it on the object if supported, or pass via bind/config
        
        # Note: ChatOpenAI.bind(temperature=...) returns a Runnable
        runnable = self.llm.bind(temperature=temperature)
        
        for chunk in runnable.stream(messages):
            if chunk.content:
                yield chunk.content

    def chat(self, messages: list[BaseMessage], temperature: float = 0.7) -> str:
        """Non-streaming chat."""
        runnable = self.llm.bind(temperature=temperature)
        response = runnable.invoke(messages)
        return response.content

