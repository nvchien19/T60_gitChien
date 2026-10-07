from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OcrModel = Literal[
    'configured', 'auto', 'gemini-3.1-flash-lite', 'gemini-3.5-flash-lite',
    'gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3.7-flash', 'gemini-3.8-flash',
]


class OcrImageRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: OcrModel = 'configured'
    mime_type: Literal['image/png', 'image/jpeg', 'image/webp']
    image_base64: str = Field(min_length=1, max_length=5600000)


class OcrMedication(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    dose: str = Field(max_length=200)
    frequency: str = Field(max_length=2000)
    quantity: str = Field(max_length=100)
    uncertain_fields: list[Literal['name', 'dose', 'frequency', 'quantity']] = Field(max_length=4)


class OcrExtraction(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(max_length=150)
    raw_text: str = Field(max_length=30000)
    medications: list[OcrMedication] = Field(max_length=50)
    warnings: list[str] = Field(max_length=50)


class OcrResponse(OcrExtraction):
    model: str
    provider: Literal['gemini'] = 'gemini'
    attempted_models: list[str] = Field(default_factory=list)
