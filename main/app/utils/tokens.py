import tiktoken


class TokenManager:
    def __init__(self, model):
        self.prompt_tokens_used = 0
        self.rag_tokens_used = 0
        self.few_shot_tokens_used = 0
        self.model = model
        self.queries = {}

    def find_query_amount(self, name):
        for query_key in self.queries.keys():
            if name in query_key:
                return self.queries[query_key]
        return 0

    def add_query(self, name, text):
        self.queries[name] = 0
        self.queries[name] += self.prompt_tokens_used
        self.queries[name] += self.num_tokens_from_string(text)

    def show_queries(self):
        return {key: format_tokens(value) for key, value in self.queries.items()}

    def get_prompt_tokens_used(self):
        return self.prompt_tokens_used

    def get_rag_tokens_used(self):
        return self.rag_tokens_used

    def get_few_shot_tokens_used(self):
        return self.few_shot_tokens_used

    def update_prompt_tokens_used(self, text):
        self.prompt_tokens_used += self.num_tokens_from_string(text)

    def update_rag_tokens_used(self, text):
        self.rag_tokens_used += self.num_tokens_from_string(text)

    def update_few_shot_tokens_used(self, text):
        self.few_shot_tokens_used += self.num_tokens_from_string(text)

    def num_tokens_from_string(self, string: str) -> int:
        default_encoding = "cl100k_base"
        model_to_encoding = {
            "gpt-4o-2024-05-13": default_encoding,
            "gpt-3.5-turbo-0125": default_encoding,
            # "llama3": "llama3",
        }
        encoding_name = (
            model_to_encoding[self.model]
            if self.model in model_to_encoding
            else default_encoding
        )

        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def get_variables_usage(self):
        return {
            "prompt": format_tokens(self.get_prompt_tokens_used()),
            "few_shot": format_tokens(self.get_few_shot_tokens_used()),
            "queries": self.show_queries(),
            "total": format_tokens(
                self.get_prompt_tokens_used()
                + self.get_few_shot_tokens_used()
                + sum(self.queries.values())
            ),
        }

    def get_workflow_usage(self):
        return {
            "prompt": format_tokens(self.get_prompt_tokens_used()),
            "few_shot": format_tokens(self.get_few_shot_tokens_used()),
            "queries": self.show_queries(),
            "total": format_tokens(
                self.get_prompt_tokens_used()
                + self.get_few_shot_tokens_used()
                + sum(self.queries.values())
            ),
        }

    def get_syntactic_refinement_usage(self):
        return {
            "queries": self.show_queries(),
            "total": format_tokens(sum(self.queries.values())),
        }

    def get_usage(self, extracted_fields_count):
        total = max(
            self.get_prompt_tokens_used()
            + self.get_rag_tokens_used()
            + self.get_few_shot_tokens_used(),
            1,
        )

        format_percentage = lambda amount: f"{round(amount / total, 2) * 100}%"
        get_formatted_values = lambda amount: {
            "absolute": format_tokens(amount),
            "relative": format_percentage(amount),
        }

        return {
            "prompt": get_formatted_values(self.get_prompt_tokens_used()),
            "queries": self.show_queries(),
            "rag": get_formatted_values(self.get_rag_tokens_used()),
            "few_shot": get_formatted_values(self.get_few_shot_tokens_used()),
            "total": format_tokens(total),
            "average": format_tokens(round((total) / extracted_fields_count)),
        }


format_tokens = lambda amount: f"{amount} tokens"
