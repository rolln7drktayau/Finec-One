"""Start the app on local loopback only. Use a production ASGI setup after hardening."""
import uvicorn
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
