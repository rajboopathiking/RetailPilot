
"""
app.py — LangServe + UnifiedNexus Hybrid Application
"""

import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableLambda
from langserve import add_routes

from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from jwt import InvalidTokenError
import jwt

from unified_nexus import UnifiedNexus

from agent.chat_app import chat_resonse,chat_resonse_stream
from utils.tools import get_details, invoice_generator

from agent.supportAgent.tools import engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

password_hash = PasswordHash.recommended()
oauth_schema = OAuth2PasswordBearer(tokenUrl="/login")

import os

JWT_SECRET= os.getenv('JWT_SECRET')
ALGORITHM = "HS256"


def hash_password(password):
    return password_hash.hash(password)

def verify_password(password,hashed):
    return password_hash.verify(password,hashed)


# --------------------------------------------------
# 1. Request Models
# --------------------------------------------------

class AgentRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)



class DBFetch(BaseModel):
    user_name: str = Field(min_length=1)
    phone_number: str = Field(min_length=1)
    components: list[str] = Field(default_factory=list)

class Auth(BaseModel):
    email : str
    password : int

class AgentRequest_Auth(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)

class Invoice(BaseModel):
    user_name: str = Field(min_length=1)
    price: str = Field(min_length=1)
    product: str = Field(min_length=1)
    date: str = Field(min_length=1)


# --------------------------------------------------
# 2. LangChain LCEL Runnable
# --------------------------------------------------

async def process_agent_request(
    data: dict[str, Any]
) -> dict[str, Any]:
    """Process a customer support request."""

    request = AgentRequest.model_validate(data)

    response = await chat_resonse(
        query=request.query,
        thread_id=request.thread_id
    )

    return {"response": response}


chain = RunnableLambda(process_agent_request)




# --------------------------------------------------
# 3. Initialize UnifiedNexus
# --------------------------------------------------

nexus = UnifiedNexus("Customer Support Agent")


# --------------------------------------------------
# 4. REST-only endpoints
# --------------------------------------------------

@nexus.api_only("/details")
def root():
    """Return service information."""
    return {
        "service": "Customer Support Agent",
        "version": "1.0.0",
        "interfaces": {
            "docs": "/docs",
            "agent": "/agent/invoke",
            "playground": "/agent/playground/",
            "dashboard": "/dashboard",
            "mcp": "/mcp",
            "health": "/health",
            "customer_details": "/get_details",
        },
    }


@nexus.api_only("/health")
def health_check():
    """Return application liveness status."""
    return {
        "status": "healthy",
        "service": "Customer Support Agent",
    }



# --------------------------------------------------
# 5. Universal REST + MCP tool
# --------------------------------------------------

@nexus.universal_tool(path="/get_details")
async def get_details_from_db(data: DBFetch):
    """
    Retrieve authorized customer information.

    Fetch requested customer components from the
    customer database.
    """

    try:
        # SECURITY:
        # Authentication and customer-level authorization
        # must be enforced in the database service.
        # User-supplied names and phone numbers are
        # identifiers, not proof of authorization.

        response = await get_details.ainvoke({
            "user_name": data.user_name,
            "phone_number": data.phone_number,
            "component": data.components,
        })

        if not response:
            return {
                "status": "not_found",
                "response": [],
            }

        return {
            "status": "success",
            "response": response,
        }

    except Exception:
        logger.exception("Customer lookup failed")
        raise HTTPException(
            status_code=500,
            detail="Customer lookup failed",
        )


# --------------------------------------------------
# 6. MCP-only tools
# --------------------------------------------------

@nexus.mcp_only
async def invoice_generate(data: Invoice):
    """
    Generate an invoice for an authorized customer.

    Requires validated customer, product, price,
    and purchase date information.
    """

    try:
        # Verify invoice ownership and retrieve trusted
        # purchase data before generating real invoices.
        result = await invoice_generator.ainvoke({
            "user_name": data.user_name,
            "price": data.price,
            "product": data.product,
            "date": data.date,
        })

        return {
            "status": "success",
            "response": result,
        }

    except Exception:
        logger.exception("Invoice generation failed")
        raise HTTPException(
            status_code=500,
            detail="Invoice generation failed",
        )


@nexus.mcp_only
def get_system_metrics():
    """Return basic application status."""

    return {
        "status": "healthy",
        "interfaces": [
            "FastAPI",
            "LangServe",
            "MCP",
        ],
    }


from pydataui import mount
from chat_ui import chat_app





# --------------------------------------------------
# 7. Build FastAPI + LangServe + UnifiedNexus
# --------------------------------------------------

app = FastAPI(
    title="Customer Support Agent",
    version="1.0.0",
    swagger_ui_parameters={
        "filter":True
    }
)

# Register LangServe routes first
add_routes(
    app,
    chain,
    path="/agent",
    input_type=AgentRequest,
    output_type=dict,
)

# Mount PyDataUI Chat Dashboard at /dashboard
mount(app, chat_app, path="/dashboard")

# Attach UnifiedNexus to the existing application
nexus.attach_to(
    app,
    api_prefix="",
    mcp_path="/mcp",
    mode="both",
)

# Verify route registration
@app.on_event("startup")
async def show_routes():
    print("\nREGISTERED ROUTES:")
    for route in app.routes:
        print(
            getattr(route, "path", ""),
            getattr(route, "methods", ""),
        )


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}




import os
import jwt

from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm
)
from jwt import InvalidTokenError
from sqlalchemy import text

JWT_SECRET = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"


oauth_schema = OAuth2PasswordBearer(tokenUrl="login")


def create_token(user_id: str):
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=ALGORITHM
    )


@app.post("/login")
def authentication(
    form: OAuth2PasswordRequestForm = Depends()
):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT customer_id, password
                FROM login_credentials
                WHERE email = :email
            """),
            {"email": form.username}
        ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # Temporary: only for existing plaintext passwords
    if row["password"] is None or not (
        form.password == str(row["password"])
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token(str(row["customer_id"]))

    return {
        "access_token": token,
        "token_type": "bearer"
    }


def get_current_user(
    token: str = Depends(oauth_schema)
):
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not isinstance(user_id, str) or not user_id:
            raise InvalidTokenError("Invalid subject")

        return user_id

    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


# 4. Protected Chat
@app.post("/chat", tags=["chat"])
async def chat_response(
    request: AgentRequest_Auth,
    user_id: str = Depends(get_current_user)
):
    response = await chat_resonse(
        query=request.query+f"\n customer specific authenticate info : customer_id : {user_id}",
        thread_id=request.thread_id
    )

    return {
        "customer_id": user_id,
        "response": response
    }



# @app.post("/login")
# def authentication(auth: Auth):
#     with engine.connect() as conn:
#         result = conn.execute(
#             text("""
#                 SELECT customer_id, full_name
#                 FROM login_credentials
#                 WHERE email = :email
#                   AND password = :password
#             """),
#             {
#                 "email": auth.email,
#                 "password": auth.password
#             }
#         )

#         row = result.fetchone()
#         user_id = row["customer_id"] if row else False
#         token = create_token(user_id=user_id)
        
#         return {
#         "access_token": token,
#         "token_type": "bearer",
#     }
    
# def get_current_user(token:str=Depends(oauth_schema)):
#     user = jwt.decode(
#         token,
#         JWT_SECRET,
#         algorithms=[ALGORITHM]
#     )
#     return user["sub"]


# @app.post("/chat",tags=["chat"])
# async def chat_response(request:AgentRequest_Auth, user_id:str=Depends(get_current_user)):
#     response = await chat_resonse(
#                 query=request.query+f"\n customer specific authenticate info : customer_id : {user_id}",
#                 thread_id=request.thread_id
#             )
#     return {"response":response}

### Streaming tokens 

from sse_starlette import EventSourceResponse

@app.post("/stream_example",tags=["demo"])
async def chat_response_stream(request:AgentRequest_Auth,user_id:str=Depends(get_current_user)):
    async def get_token():
        response = await chat_resonse_stream(
                    query=request.query+f"\n customer specific authenticate info : customer_id : {user_id}",
                    thread_id=request.thread_id
                )
        yield response
    return EventSourceResponse(get_token())


# --------------------------------------------------
# 8. Run Server
# --------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )
