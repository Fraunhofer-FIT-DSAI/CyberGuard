from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from langchain.schema.runnable import RunnableLambda

from fastapi import FastAPI
from langserve import add_routes

from app.routes.cacao_questions import handler as cacao_questions_handler
from app.routes.playbook import handler as playbook_handler
from app.routes.main import handler as main_handler
from app.routes.llama import handler as llama_handler
from app.routes.roaster import handler as roaster_handler
from app.routes.evaluation import handler as evaluation_handler
from app.routes.translation_script import handler as translation_script_handler
from app.routes.evaluation_script import handler as evaluation_script_handler
from app.routes.analyze import handler as analyze_handler

app = FastAPI()

# Answer questions based on CACAO
add_routes(
    app,
    RunnableLambda(cacao_questions_handler),
    path="/cacao-questions",
)

# Answer questions based on playbook and CACAO
add_routes(
    app,
    RunnableLambda(playbook_handler),
    path="/playbook",
)

# Translate Playbook to CACAO
add_routes(
    app,
    RunnableLambda(main_handler),
    path="/main",
)

add_routes(
    app,
    RunnableLambda(evaluation_handler),
    path="/evaluation",
)

add_routes(
    app,
    RunnableLambda(translation_script_handler),
    path="/translation_script",
)

add_routes(
    app,
    RunnableLambda(evaluation_script_handler),
    path="/evaluation_script",
)

add_routes(
    app,
    RunnableLambda(analyze_handler),
    path="/analyze",
)

add_routes(
    app,
    RunnableLambda(llama_handler),
    path="/llama",
)

add_routes(
    app,
    RunnableLambda(roaster_handler),
    path="/roaster",
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
