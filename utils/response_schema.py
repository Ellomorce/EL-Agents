from pydantic import BaseModel

# class CRPOCR(BaseModel):

class Triztags(BaseModel):
    actions: list[str]
    objects: list[str]