from fastapi import FastAPI, UploadFile, Form
from services import ocr_service, liveness_service, face_match_service
from database import init_db
import uvicorn

app = FastAPI(title="Biometric Verification API")

# Initialize DB
init_db()

@app.post("/verify")
async def verify_user(
    name: str = Form(...),
    id_image: UploadFile = None,
    live_image: UploadFile = None
):
    # OCR Extraction
    id_data = await ocr_service.extract_text(id_image)

    # Liveness Detection
    live_status = await liveness_service.check_liveness(live_image)

    # Face Matching
    match_result = await face_match_service.compare_faces(id_image, live_image)

    return {
        "name": name,
        "id_data": id_data,
        "liveness": live_status,
        "face_match": match_result
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
