from fastapi import FastAPI 


testapp = FastAPI() 


@testapp.get("/")
def root():
    name = "moussa"
    return "hello " + name