import json
import webbrowser
import urllib.parse
from langserve import CustomUserType
from typing import Literal

import os
import subprocess

from app.extraction.utils import get_final_file_name
from app.routes.main import AVAILABLE_UNSTRUCTURED_PLAYBOOKS, Model

class Dependencies(CustomUserType):
    playbook_file_name: AVAILABLE_UNSTRUCTURED_PLAYBOOKS = (
        "AWS_IAM_Account_Locking.json"
    )
    text_content: str = ""
    model: Model = "gpt-3.5-turbo-0125"
    flow: Literal['visualize','validate'] = 'visualize'


def handler(dependencies: Dependencies):
    file_name = get_final_file_name(dependencies)
    
    if dependencies.flow == 'visualize':
        with open(file_name, "r") as file:
            playbook = json.load(file)
        url_encoded_playbook = urllib.parse.quote(json.dumps(playbook))
        url = f"http://localhost:3000/?playbook={url_encoded_playbook}"
        webbrowser.open_new_tab(url)
        
    if dependencies.flow == 'validate':
        if(dependencies.text_content != ""):
            file_name = f"outputs/text.json"
            with open(file_name, "w") as file:
                file.write(dependencies.text_content)
                
        absolute_path = os.path.abspath(file_name)
        
        script = "/Users/devicedev/Documents/RWTH/6 Semester/Thesis/cacao-roaster/src/app/multi-instance/SyntaxChecker.js"
        command=f"node \"{script}\" \"{absolute_path}\""
        
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result.stdout
