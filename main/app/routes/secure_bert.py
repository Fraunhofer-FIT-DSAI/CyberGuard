from langserve import CustomUserType
from app.utils.files import get_unstructured_playbook_content

import torch
import transformers
from transformers import RobertaTokenizerFast, RobertaTokenizer, RobertaModel

tokenizer = RobertaTokenizerFast.from_pretrained("ehsanaghaei/SecureBERT")
model = transformers.RobertaForMaskedLM.from_pretrained("ehsanaghaei/SecureBERT")


def predict_mask(sent, tokenizer, model, topk=10, print_results=True):
    token_ids = tokenizer.encode(sent, return_tensors="pt")
    masked_position = (token_ids.squeeze() == tokenizer.mask_token_id).nonzero()
    masked_pos = [mask.item() for mask in masked_position]
    words = []
    with torch.no_grad():
        output = model(token_ids)

    last_hidden_state = output[0].squeeze()

    list_of_list = []
    for index, mask_index in enumerate(masked_pos):
        mask_hidden_state = last_hidden_state[mask_index]
        idx = torch.topk(mask_hidden_state, k=topk, dim=0)[1]
        words = [tokenizer.decode(i.item()).strip() for i in idx]
        words = [w.replace(" ", "") for w in words]
        list_of_list.append(words)
        if print_results:
            print("Mask ", "Predictions : ", words)

    best_guess = ""
    for j in list_of_list:
        best_guess = best_guess + "," + j[0]

    return words


class BertInput(CustomUserType):
    question: str = "The name of the playbook is <mask>"
    playbook_file_name: str = "AWS_IAM_Account_Locking.json"


def handler(input: BertInput):
    playbook = get_unstructured_playbook_content(input.playbook_file_name)
    # RuntimeError: The expanded size of the tensor (2243) must match the existing size (514) at non-singleton dimension 1.  Target sizes: [1, 2243].  Tensor sizes: [1, 514]
    template = f"""
        Question: {input.question}
        Playbook: {playbook}        
    """

    words = predict_mask(template, tokenizer, model)
    print(words)
    return {"words": words}
