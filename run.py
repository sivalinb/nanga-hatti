import argparse
import uvicorn
from nanga.app import create_app

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Run your local Nanga Hatti workspace")
    parser.add_argument("--port",type=int,default=8787)
    args=parser.parse_args()
    uvicorn.run(create_app(),host="127.0.0.1",port=args.port,proxy_headers=False)
