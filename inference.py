from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any
from env.environment import CodeReviewEnv
from env.models import Action

app = FastAPI()
env = CodeReviewEnv()


class ActionRequest(BaseModel):
    issues: list[Any] = []
    final_decision: str = "approve"


@app.post("/reset")
def reset():
    obs = env.reset()
    return obs.model_dump()


@app.post("/step")
def step(action_req: ActionRequest):
    action = Action(**action_req.model_dump())
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": info,
    }


@app.get("/state")
def state():
    return env.state()
