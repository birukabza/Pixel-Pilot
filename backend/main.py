from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import service
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()


class GenerateRequest(BaseModel):
    model: str
    contents: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = None


@app.post("/v1/generate")
async def generate(request: GenerateRequest):
    try:
        # The instruction implies a direct call to generate_content,
        # assuming service.generate_content can now accept GenerateRequest directly
        # or that generate_content is imported directly.
        # Given the original code, it's more likely service.generate_content is still used
        # and the instruction's snippet simplified it for brevity.
        # I will adapt to call service.generate_content with the original GenerationRequest structure
        # but incorporate the new error handling.
        logger.info(f"Generating content with model: {request.model}")
        result = await service.generate_content(
            service.GenerationRequest(
                model=request.model, contents=request.contents, config=request.config
            )
        )
        return result
    except Exception as e:
        # Check if it's a Google API error with a status code
        status_code = 500
        if hasattr(e, "code"):
            status_code = e.code
        elif hasattr(e, "status_code"):
            status_code = e.status_code

        # Log the error
        logger.error(f"Generation error: {e}")

        # Raise HTTP exception with the correct status code
        raise HTTPException(status_code=status_code, detail=str(e))


@app.get("/health")
async def health_check():  # Renamed and made async
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
