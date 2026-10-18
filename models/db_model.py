from pydantic import BaseModel,Field
from datetime import datetime
from typing import Literal

class UserInput(BaseModel):
  name : str 
  phone_number : str
  created_at : datetime = Field(datetime.now())
  item : str
  price : str
  delivery_type : str
  delivery_status : Literal["pending","out of delivery","failed"]
  location : str
  address : str


from typing import List,Dict,TypedDict,Annotated
from langchain_core.messages import BaseMessage,AIMessage,HumanMessage,AnyMessage,ToolMessage
from langgraph.graph.message import add_messages
class MessageState(TypedDict):
  """Manage States across nodes"""
  messages : Annotated[List[BaseMessage],add_messages]
