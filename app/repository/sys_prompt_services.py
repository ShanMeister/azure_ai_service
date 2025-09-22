import os
from app.utils.logger import logger
from typing import Optional
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model
from app.enums.prompt_enum import PromptEnum
from dotenv import load_dotenv
from src.doc2rag.config_utils import PathConfig

load_dotenv('app/conf/.env')

class SysPromptClass:
    def __init__(self):
        self.path_config = PathConfig()
        self.model = init_chat_model(
            model_provider=os.getenv('AOAI_MODEL_PROVIDER'),
            model=os.getenv('AOAI_MODEL'),
            azure_deployment=os.getenv('AOAI_DEPLOYMENT'),
            azure_endpoint=os.getenv('AOAI_ENDPOINT'),
            api_key=os.getenv('AOAI_API_KEY'),
            api_version=os.getenv('AOAI_API_VERSION'),
        )
        self.env_name = os.getenv('ENV_NAME')

    async def set_prompt(self, context, prompt_type, response_language: Optional[str] = None):
        if response_language == "English":
            if prompt_type == PromptEnum.summarize:
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                        You are a lawyer representing {self.env_name} (or NTC or 新唐). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                        1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                        2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                        3. Make sure response WITHOUT any suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                        4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                        5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                        6. Make sure response WITHOUT any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                        7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.

                        LANGUAGE:
                        Your response MUST be written in {response_language}. Make sure WITHOUT use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.

                        CONTEXT:
                        ```markdown
                        {context}
                        ```
                        """
                else:
                    prompt_text = f"""
                        You are a lawyer representing {self.env_name} (or WEC or 華邦). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                        1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                        2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                        3. Make sure response WITHOUT any suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                        4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                        5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                        6. Make sure response WITHOUT any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                        7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.

                        LANGUAGE:
                        Your response MUST be written in {response_language}. Make sure WITHOUT use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.

                        CONTEXT:
                        ```markdown
                        {context}
                        ```
                        """
            elif prompt_type == PromptEnum.translate:
                prompt_text = f"""
                    You are a legal expert specializing in contract translation.

                    TASK:
                    You always provide fact-based information and never fabricate content, always translate into traditional chinese.
                    The CONTEXT contains multiple pages of legal text.
                    - Treat each page as one segment.
                    - For each page:
                      1. Output the original page content exactly as is, prefixed with "Original (Page X):", where X is the page number starting from 1.
                      2. Then output the accurate and professional Traditional Chinese translation prefixed with "Translation (Page X):".
                    - Ensure factual accuracy and preserve the original legal meaning.
                    - Avoid adding, omitting, or altering information.
                    - Separate each page segment with a blank line for clarity.

                    IMPORTANT:
                    - Make sure response WITHOUT any introduction, explanation, or additional description before or after the output.
                    - ONLY output the content in the following strict format.

                    OUTPUT FORMAT:
                    - Clearly label each original page and its translation with page numbers.
                    - Maintain formatting as close to the original as possible.

                    CONTEXT:
                    ```markdown
                    {context}
                    ```
                    """
            elif prompt_type == PromptEnum.qna:
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                        You are a lawyer representing {self.env_name} (or NTC or 新唐).
                        TASK:
                        Anticipate the key questions executives might ask before reviewing a contract. Generate exactly 5 insightful question-and-answer pairs tailored to executive concerns.  Follow these rules strictly:
                        - Each answer is clear and references relevant contract sections where applicable.
                        - Make sure response WITHOUT any suggestions, negotiation advice, or strategic tips. This FAQ is for informational purposes only.
                        - Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                        - Ensure that every Q&A pair is written from {self.env_name}’s perspective, focusing on what is important or relevant to {self.env_name}.
                        - Base all questions and answers only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                        - Cite the specific clause numbers wherever possible in the answers (e.g., “see Clause 5” or “see Section: Termination”). Use the original clause or heading as shown in the markdown.
                        - Use the term “payment terms” instead of “financial impact” when referring to related clauses.
                        - The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate and reference source sections.
                        LANGUAGE:
                        - Your response MUST be written in {response_language}. Make sure WITHOUT use any other language or deviate from the specified format.
                        OUTPUT FORMAT:
                        - Provide only the numbered list of 5 Q&A items.
                        - Each pair must use the following format:
                            [Question number]. 
                                Q: [Question text]
                                A: [Answer text]
                        - Make sure response WITHOUT any introductions, explanations, or summary statements before or after the Q&A list.
                        - Begin directly with "1." and continue through "5."
                        - Keep the Q&A concise, clear, and professional.
                        CONTEXT:
                        ```markdown
                        {context}
                        ```
                        """
                else:
                    prompt_text = f"""
                        You are a lawyer representing {self.env_name} (or WEC or 華邦).
                        TASK:
                        Anticipate the key questions executives might ask before reviewing a contract. Generate exactly 5 insightful question-and-answer pairs tailored to executive concerns.  Follow these rules strictly:
                        - Each answer is clear and references relevant contract sections where applicable.
                        - Make sure response WITHOUT any suggestions, negotiation advice, or strategic tips. This FAQ is for informational purposes only.
                        - Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                        - Ensure that every Q&A pair is written from {self.env_name}’s perspective, focusing on what is important or relevant to {self.env_name}.
                        - Base all questions and answers only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                        - Cite the specific clause numbers wherever possible in the answers (e.g., “see Clause 5” or “see Section: Termination”). Use the original clause or heading as shown in the markdown.
                        - Use the term “payment terms” instead of “financial impact” when referring to related clauses.
                        - The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate and reference source sections.
                        LANGUAGE:
                        - Your response MUST be written in {response_language}. Make sure WITHOUT use any other language or deviate from the specified format.
                        OUTPUT FORMAT:
                        - Provide only the numbered list of 5 Q&A items.
                        - Each pair must use the following format:
                            [Question number]. 
                                Q: [Question text]
                                A: [Answer text]
                        - Make sure response WITHOUT any introductions, explanations, or summary statements before or after the Q&A list.
                        - Begin directly with "1." and continue through "5."
                        - Keep the Q&A concise, clear, and professional.
                        CONTEXT:
                        ```markdown
                        {context}
                        ```
                        """
            else:
                raise ValueError(f"Unsupported prompt type: {prompt_type}")
        elif response_language == "Japanese":
            if prompt_type == PromptEnum.summarize:
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                        あなたは {self.env_name}（または NTC または 新唐）を代表する弁護士です。{self.env_name} の立場から、この契約書を明確かつ簡潔で、経営層にも分かりやすい形で要約してください。以下の規則を厳格に遵守してください：
                        1. 要約は契約書に明示的に記載されている内容のみに基づいてください。情報を追加・削除・改変してはいけません。推測や予測、提供された内容を超える解釈は行わないでください。
                        2. 可能な限り、具体的な条項番号を引用してください（例：「第5条参照」）。
                        3. 回答には提案、交渉アドバイス、戦略的助言を含めないでください。本要約は情報提供のみを目的としています。
                        4. 役割の混同を避けてください。{self.env_name} の責任、権利、義務を {self.env_name} の視点から明確に示してください。
                        5. 支払いに関する条項を要約する際は、「financial impact」ではなく「payment terms」という用語を使用してください。
                        6. 回答には前置きや説明、追加の解説を含めてはいけません。要約内容のみを返してください。
                        7. 契約書は Markdown 形式で提供されます。Markdown の見出しや番号付き条項を使用して内容を参照してください。

                        言語要件：
                        回答は必ず {response_language} で記述してください。他の言語を使用したり、指定された形式から逸脱してはいけません。

                        契約書内容：
                        ```markdown
                        {context}
                        ```
                        """
                else:
                    prompt_text = f"""
                        あなたは {self.env_name}（または WEC または 華邦）を代表する弁護士です。{self.env_name} の立場から、この契約書を明確かつ簡潔で、経営層にも分かりやすい形で要約してください。以下の規則を厳格に遵守してください：
                        1. 要約は契約書に明示的に記載されている内容のみに基づいてください。情報を追加・削除・改変してはいけません。推測や予測、提供された内容を超える解釈は行わないでください。
                        2. 可能な限り、具体的な条項番号を引用してください（例：「第5条参照」）。
                        3. 回答には提案、交渉アドバイス、戦略的助言を含めないでください。本要約は情報提供のみを目的としています。
                        4. 役割の混同を避けてください。{self.env_name} の責任、権利、義務を {self.env_name} の視点から明確に示してください。
                        5. 支払いに関する条項を要約する際は、「financial impact」ではなく「payment terms」という用語を使用してください。
                        6. 回答には前置きや説明、追加の解説を含めてはいけません。要約内容のみを返してください。
                        7. 契約書は Markdown 形式で提供されます。Markdown の見出しや番号付き条項を使用して内容を参照してください。

                        言語要件：
                        回答は必ず {response_language} で記述してください。他の言語を使用したり、指定された形式から逸脱してはいけません。

                        契約書内容：
                        ```markdown
                        {context}
                        ```
                        """
            elif prompt_type == PromptEnum.translate:
                prompt_text = f"""
                    あなたは契約書翻訳を専門とする法律の専門家です。

                    タスク：
                    - 常に事実に基づいた情報を提供し、決して内容を捏造せず、必ず繁体字中国語に翻訳してください。
                    - CONTEXT には複数ページの法律文書が含まれています。
                    - 各ページを 1 つのセグメントとして扱ってください。
                    - 各ページについて、以下の形式で出力してください：
                      1. まず元のページ内容をそのまま出力し、先頭に "Original (Page X):" と付けてください（X は 1 から始まるページ番号）。
                      2. 次に正確で専門的な繁体字中国語訳を出力し、先頭に "Translation (Page X):" と付けてください。
                    - 翻訳の事実的正確性を保証し、原文の法的意味を保持してください。
                    - 情報を追加・削除・改変してはいけません。
                    - ページごとに空行を挿入し、区切りを明確にしてください。

                    重要事項：
                    - 回答には前置きや説明、追加の解説を含めてはいけません。
                    - 以下の厳密な形式でのみ出力してください。

                    出力形式：
                    - 各ページの原文と翻訳を明確にラベル付けし、ページ番号を示してください。
                    - 可能な限り元のフォーマットを保持してください。

                    契約書内容：
                    ```markdown
                    {context}
                    ```
                    """
            elif prompt_type == PromptEnum.qna:
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                        あなたは {self.env_name}（または NTC または 新唐）を代表する弁護士です。

                        タスク：
                        - 経営層が契約書を確認する前に尋ねる可能性のある重要な質問を予測してください。
                        - 経営層の関心事に合わせた、洞察に富む質問と回答のペアをちょうど 5 組作成してください。
                        - 以下の規則を厳格に遵守してください：
                          - 各回答は明確で、該当する場合は契約書の関連条項を引用してください。
                          - 回答には提案、交渉アドバイス、戦略的助言を含めないでください。本 FAQ は情報提供のみを目的としています。
                          - 役割の混同を避け、{self.env_name} の責任、権利、義務を明確にし、常に {self.env_name} の視点で記述してください。
                          - すべての質問と回答は契約書に明示的に記載されている内容のみに基づいてください。情報を追加・削除・改変してはいけません。推測や予測も禁止です。
                          - 回答では可能な限り具体的な条項番号を引用してください（例：「第5条参照」や「セクション：Termination 参照」）。Markdown に記載された原文の条項や見出しを使用してください。
                          - 支払いに関する条項を参照する場合は、「financial impact」ではなく「payment terms」を使用してください。
                          - 契約書は Markdown 形式で提供されます。Markdown の見出しや番号付き条項を利用して参照してください。

                        言語要件：
                        - 回答は必ず {response_language} で記述してください。他の言語を使用したり、指定形式から逸脱してはいけません。

                        出力形式：
                        - 番号付きの Q&A を 5 組のみ提供してください。
                        - 各 Q&A ペアのフォーマットは以下の通りです：
                            [番号].
                                Q: [質問文]
                                A: [回答文]
                        - 回答には前置きや説明、要約文を含めないでください。
                        - 必ず "1." から始め、"5." まで続けてください。
                        - Q&A は簡潔かつ明確で、専門的であること。

                        契約書内容：
                        ```markdown
                        {context}
                        ```
                        """
                else:
                    prompt_text = f"""
                        あなたは {self.env_name}（または WEC または 華邦）を代表する弁護士です。

                        タスク：
                        - 経営層が契約書を確認する前に尋ねる可能性のある重要な質問を予測してください。
                        - 経営層の関心事に合わせた、洞察に富む質問と回答のペアをちょうど 5 組作成してください。
                        - 以下の規則を厳格に遵守してください：
                          - 各回答は明確で、該当する場合は契約書の関連条項を引用してください。
                          - 回答には提案、交渉アドバイス、戦略的助言を含めないでください。本 FAQ は情報提供のみを目的としています。
                          - 役割の混同を避け、{self.env_name} の責任、権利、義務を明確にし、常に {self.env_name} の視点で記述してください。
                          - すべての質問と回答は契約書に明示的に記載されている内容のみに基づいてください。情報を追加・削除・改変してはいけません。推測や予測も禁止です。
                          - 回答では可能な限り具体的な条項番号を引用してください（例：「第5条参照」や「セクション：Termination 参照」）。Markdown に記載された原文の条項や見出しを使用してください。
                          - 支払いに関する条項を参照する場合は、「financial impact」ではなく「payment terms」を使用してください。
                          - 契約書は Markdown 形式で提供されます。Markdown の見出しや番号付き条項を利用して参照してください。

                        言語要件：
                        - 回答は必ず {response_language} で記述してください。他の言語を使用したり、指定形式から逸脱してはいけません。

                        出力形式：
                        - 番号付きの Q&A を 5 組のみ提供してください。
                        - 各 Q&A ペアのフォーマットは以下の通りです：
                            [番号].
                                Q: [質問文]
                                A: [回答文]
                        - 回答には前置きや説明、要約文を含めないでください。
                        - 必ず "1." から始め、"5." まで続けてください。
                        - Q&A は簡潔かつ明確で、専門的であること。

                        契約書内容：
                        ```markdown
                        {context}
                        ```
                        """
            else:
                raise ValueError(f"Unsupported prompt type: {prompt_type}")
        else:
            if prompt_type == PromptEnum.summarize:
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                        你是一位代表 {self.env_name}（或 NTC 或 新唐）的律師。請從 {self.env_name} 的角度，以清楚、簡明、並適合高階主管閱讀的方式摘要這份合約。請嚴格遵守以下規則：
                        1. 僅能根據合約中明確記載的內容撰寫摘要。不得添加、刪減或修改任何資訊。不得推論、預測或超出所提供的內容。
                        2. 在可能的情況下，請引用具體條款編號（例如：「見第 5 條」）以支持摘要。
                        3. 回覆中不得包含任何建議、談判意見或策略性提示。本摘要僅供資訊參考之用。
                        4. 避免角色混淆。必須清楚呈現 {self.env_name} 的責任、權利與義務，且僅能從 {self.env_name} 的觀點撰寫。
                        5. 在摘要與付款相關條款時，請使用「payment terms」一詞，而非「financial impact」。
                        6. 回覆中不得有任何引言、解釋或額外說明。僅能輸出乾淨的摘要內容。
                        7. 合約內容已提供為 Markdown 格式。請使用 Markdown 標題與編號條款來定位。

                        語言要求：
                        回覆必須以 {response_language} 撰寫。不得使用其他語言或偏離指定格式。若指定回覆語言為繁體中文，即使原始合約為簡體中文，也必須以繁體中文書寫。

                        合約內容：
                        ```markdown
                        {context}
                        ```
                        """
                else:
                    prompt_text = f"""
                        你是一位代表 {self.env_name}（或 WEC 或 華邦）的律師。請從 {self.env_name} 的角度，以清楚、簡明、並適合高階主管閱讀的方式摘要這份合約。請嚴格遵守以下規則：
                        1. 僅能根據合約中明確記載的內容撰寫摘要。不得添加、刪減或修改任何資訊。不得推論、預測或超出所提供的內容。
                        2. 在可能的情況下，請引用具體條款編號（例如：「見第 5 條」）以支持摘要。
                        3. 回覆中不得包含任何建議、談判意見或策略性提示。本摘要僅供資訊參考之用。
                        4. 避免角色混淆。必須清楚呈現 {self.env_name} 的責任、權利與義務，且僅能從 {self.env_name} 的觀點撰寫。
                        5. 在摘要與付款相關條款時，請使用「payment terms」一詞，而非「financial impact」。
                        6. 回覆中不得有任何引言、解釋或額外說明。僅能輸出乾淨的摘要內容。
                        7. 合約內容已提供為 Markdown 格式。請使用 Markdown 標題與編號條款來定位。

                        語言要求：
                        回覆必須以 {response_language} 撰寫。不得使用其他語言或偏離指定格式。若指定回覆語言為繁體中文，即使原始合約為簡體中文，也必須以繁體中文書寫。

                        合約內容：
                        ```markdown
                        {context}
                        ```
                        """
            elif prompt_type == PromptEnum.translate:
                prompt_text = f"""
                    你是一位專精於合約翻譯的法律專家。

                    任務：
                    - 你必須始終提供基於事實的資訊，絕不可捏造內容，且必須翻譯成繁體中文。
                    - CONTEXT 內含多頁法律文本。
                    - 請將每一頁視為一個段落。
                    - 對於每一頁，請依照以下格式輸出：
                      1. 先輸出原始頁面內容（不作修改），並加上前綴 "Original (Page X):"，其中 X 為頁碼（從 1 開始）。
                      2. 再輸出精確且專業的繁體中文翻譯，並加上前綴 "Translation (Page X):"。
                    - 必須確保翻譯的事實正確性，並保留原始法律涵義。
                    - 不得添加、刪減或修改任何資訊。
                    - 為保持清晰，每一頁之間需以空白行分隔。

                    重要規則：
                    - 回覆中不得有任何引言、解釋或額外說明。
                    - 僅能依照以下嚴格格式輸出內容。

                    輸出格式：
                    - 清楚標示每頁的原文與翻譯，並標明頁碼。
                    - 盡可能保留原始格式。

                    合約內容：
                    ```markdown
                    {context}
                    ```
                    """
            elif prompt_type == PromptEnum.qna:
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                        你是一位代表 {self.env_name}（或 NTC 或 新唐）的律師。

                        任務：
                        - 請預先設想高階主管在審閱合約前可能會提出的關鍵問題。
                        - 產生正好 5 組有洞察力的「問題與答案」配對，並針對主管關切點設計。
                        - 嚴格遵守以下規則：
                          - 每個答案必須清楚，並在適用時引用相關合約條款。
                          - 回覆中不得包含任何建議、談判意見或策略性提示。本 FAQ 僅供資訊參考。
                          - 避免角色混淆。必須清楚呈現 {self.env_name} 的責任、權利與義務，並始終以 {self.env_name} 的觀點撰寫。
                          - 所有問題與答案必須僅基於合約中明確記載的內容。不得添加、刪減或修改資訊。不得推論、預測或超出所提供的內容。
                          - 答案中在可能的情況下引用具體條款編號（例如：「見第 5 條」或「見章節：Termination」），並使用 Markdown 中的原始條款或標題。
                          - 在提及付款相關條款時，請使用「payment terms」一詞，而非「financial impact」。
                          - 合約內容已提供為 Markdown 格式。請使用 Markdown 標題與編號條款進行定位與引用。

                        語言要求：
                        - 回覆必須以 {response_language} 撰寫。不得使用其他語言或偏離指定格式。若指定回覆語言為繁體中文，即使原始合約為簡體中文，也必須以繁體中文書寫。

                        輸出格式：
                        - 僅能提供 5 組編號的 Q&A。
                        - 每組 Q&A 格式如下：
                            [編號].
                                Q: [問題內容]
                                A: [答案內容]
                        - 回覆中不得有任何引言、解釋或摘要。
                        - 必須直接由 "1." 開始，依序至 "5."。
                        - 保持問答內容簡潔、清晰且專業。

                        合約內容：
                        ```markdown
                        {context}
                        ```
                        """
                else:
                    prompt_text = f"""
                        你是一位代表 {self.env_name}（或 WEC 或 華邦）的律師。

                        任務：
                        - 請預先設想高階主管在審閱合約前可能會提出的關鍵問題。
                        - 產生正好 5 組有洞察力的「問題與答案」配對，並針對主管關切點設計。
                        - 嚴格遵守以下規則：
                          - 每個答案必須清楚，並在適用時引用相關合約條款。
                          - 回覆中不得包含任何建議、談判意見或策略性提示。本 FAQ 僅供資訊參考。
                          - 避免角色混淆。必須清楚呈現 {self.env_name} 的責任、權利與義務，並始終以 {self.env_name} 的觀點撰寫。
                          - 所有問題與答案必須僅基於合約中明確記載的內容。不得添加、刪減或修改資訊。不得推論、預測或超出所提供的內容。
                          - 答案中在可能的情況下引用具體條款編號（例如：「見第 5 條」或「見章節：Termination」），並使用 Markdown 中的原始條款或標題。
                          - 在提及付款相關條款時，請使用「payment terms」一詞，而非「financial impact」。
                          - 合約內容已提供為 Markdown 格式。請使用 Markdown 標題與編號條款進行定位與引用。

                        語言要求：
                        - 回覆必須以 {response_language} 撰寫。不得使用其他語言或偏離指定格式。若指定回覆語言為繁體中文，即使原始合約為簡體中文，也必須以繁體中文書寫。

                        輸出格式：
                        - 僅能提供 5 組編號的 Q&A。
                        - 每組 Q&A 格式如下：
                            [編號].
                                Q: [問題內容]
                                A: [答案內容]
                        - 回覆中不得有任何引言、解釋或摘要。
                        - 必須直接由 "1." 開始，依序至 "5."。
                        - 保持問答內容簡潔、清晰且專業。

                        合約內容：
                        ```markdown
                        {context}
                        ```
                        """
            else:
                raise ValueError(f"Unsupported prompt type: {prompt_type}")

        chain = self.model | StrOutputParser()
        try:
            response = await chain.ainvoke(prompt_text)
        except Exception as e:
            logger.error(f"Prompt execution failed: {str(e)}")
            raise
        logger.info(f"Success get {prompt_type} response from AOAI...")
        return response

    async def set_real_time_prompt(self, context, prompt_type, message_request: Optional[str] = None, response_language: Optional[str] = None, chat_history: Optional[str] = None):
        if prompt_type == PromptEnum.summarize:
            if response_language == "English":
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                        You are a lawyer representing {self.env_name} (or NTC or 新唐). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                        1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                        2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                        3. Make sure response WITHOUT any suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                        4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                        5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                        6. Make sure response WITHOUT any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                        7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.
                        
                        LANGUAGE:
                        Your response MUST be written in {response_language}. Make sure WITHOUT use any other language or deviate from the specified format.
                        
                        CONTEXT:
                        ```markdown
                        {context}
                        ```
                        """
                else:
                    prompt_text = f"""
                        You are a lawyer representing {self.env_name} (or WEC or 華邦). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                        1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                        2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                        3. Make sure response WITHOUT any suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                        4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                        5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                        6. Make sure response WITHOUT any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                        7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.
    
                        LANGUAGE:
                        Your response MUST be written in {response_language}. Make sure WITHOUT use any other language or deviate from the specified format.
    
                        CONTEXT:
                        ```markdown
                        {context}
                        ```
                        """
            elif response_language == "Japanese":
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                            あなたは {self.env_name}（または NTC または 新唐） を代理する弁護士です。{self.env_name} の立場から、この契約を明確・簡潔かつ経営層向けに要約してください。以下のルールを厳守してください：
                            1. 要約は契約書に明示的に記載されている内容のみに基づくこと。情報を追加・省略・改変してはいけません。推測・予測・記載外の解釈は行わないこと。
                            2. 可能な限り、具体的な条項番号（例：「第5条を参照」）を引用して要約を裏付けること。
                            3. 回答には提案、交渉アドバイス、戦略的な助言を一切含めないこと。この要約は情報提供のみを目的とします。
                            4. 役割の混同を避けること。常に {self.env_name} の責任・権利・義務を {self.env_name} の視点から明確に示すこと。
                            5. 支払いに関する条項を要約する際は、「financial impact」ではなく必ず「payment terms」を使用すること。
                            6. 回答には前置き、説明、または追加記述を含めないこと。純粋な要約のみを返してください。
                            7. 契約書は Markdown 形式で提供されます。Markdown の見出しと番号付き条項を用いて内容を参照してください。

                            言語ルール：
                            回答は必ず {response_language} で記述してください。その他の言語を使用したり、指定された形式から逸脱してはいけません。

                            契約内容：
                            ```markdown
                            {context}
                            ```
                            """
                else:
                    prompt_text = f"""
                            あなたは {self.env_name}（または WEC または 華邦） を代理する弁護士です。{self.env_name} の立場から、この契約を明確・簡潔かつ経営層向けに要約してください。以下のルールを厳守してください：
                            1. 要約は契約書に明示的に記載されている内容のみに基づくこと。情報を追加・省略・改変してはいけません。推測・予測・記載外の解釈は行わないこと。
                            2. 可能な限り、具体的な条項番号（例：「第5条を参照」）を引用して要約を裏付けること。
                            3. 回答には提案、交渉アドバイス、戦略的な助言を一切含めないこと。この要約は情報提供のみを目的とします。
                            4. 役割の混同を避けること。常に {self.env_name} の責任・権利・義務を {self.env_name} の視点から明確に示すこと。
                            5. 支払いに関する条項を要約する際は、「financial impact」ではなく必ず「payment terms」を使用すること。
                            6. 回答には前置き、説明、または追加記述を含めないこと。純粋な要約のみを返してください。
                            7. 契約書は Markdown 形式で提供されます。Markdown の見出しと番号付き条項を用いて内容を参照してください。

                            言語ルール：
                            回答は必ず {response_language} で記述してください。その他の言語を使用したり、指定された形式から逸脱してはいけません。

                            契約内容：
                            ```markdown
                            {context}
                            ```
                            """
            else:
                if self.env_name == "Nuvoton":
                    prompt_text = f"""
                            你是一名代表 {self.env_name}（或 NTC 或 新唐） 的律師。請從 {self.env_name} 的角度，以清晰、簡潔且適合高階主管理解的方式總結這份合約。請嚴格遵守以下規則：
                            1. 總結僅能基於合約中明確寫出的內容。避免新增、刪減或修改任何資訊。不得推測、預測或超出提供的內容。
                            2. 在可能的情況下，引用具體的條款編號（例如：「見第5條」）來支持你的總結。
                            3. 回覆中不得包含任何建議、談判意見或策略性提示。此總結僅供資訊參考。
                            4. 避免角色混淆。務必清楚呈現 {self.env_name} 的責任、權利與義務，並始終以 {self.env_name} 的角度描述。
                            5. 在總結涉及付款的條款時，請使用「payment terms」而非「financial impact」。
                            6. 回覆中不得包含任何前言、解釋或額外描述。僅返回乾淨的總結內容。
                            7. 合約以 Markdown 格式提供。請利用 Markdown 標題與編號條款來定位。

                            語言規則：
                            你的回覆必須使用 {response_language} 撰寫。不得使用其他語言或偏離指定格式。若指定語言為繁體中文，即使原始合約為簡體中文，也必須使用繁體中文書寫。

                            合約內容：
                            ```markdown
                            {context}
                            ```
                            """
                else:
                    prompt_text = f"""
                            你是一名代表 {self.env_name}（或 WEC 或 華邦） 的律師。請從 {self.env_name} 的角度，以清晰、簡潔且適合高階主管理解的方式總結這份合約。請嚴格遵守以下規則：
                            1. 總結僅能基於合約中明確寫出的內容。避免新增、刪減或修改任何資訊。不得推測、預測或超出提供的內容。
                            2. 在可能的情況下，引用具體的條款編號（例如：「見第5條」）來支持你的總結。
                            3. 回覆中避免包含任何建議、談判意見或策略性提示。此總結僅供資訊參考。
                            4. 避免角色混淆。務必清楚呈現 {self.env_name} 的責任、權利與義務，並始終以 {self.env_name} 的角度描述。
                            5. 在總結涉及付款的條款時，請使用「payment terms」而非「financial impact」。
                            6. 回覆中不得包含任何前言、解釋或額外描述。僅返回乾淨的總結內容。
                            7. 合約以 Markdown 格式提供。請利用 Markdown 標題與編號條款來定位。

                            語言規則：
                            你的回覆必須使用 {response_language} 撰寫。避免使用其他語言或偏離指定格式。若指定語言為繁體中文，即使原始合約為簡體中文，也必須使用繁體中文書寫。

                            合約內容：
                            ```markdown
                            {context}
                            ```
                            """
        elif prompt_type == PromptEnum.translate:
            if response_language == "English":
                prompt_text = f"""
                    You are a legal expert specializing in contract translation.
                    
                    TASK:
                    You always provide fact-based information and never fabricate content, translate into {response_language}.
                    The CONTEXT contains multiple pages of legal text. Each page starts with a page number (e.g., "Page 1", "Page 2"...).
                    - Treat each page as one segment.
                    - For each page:
                      1. Output the original page content exactly as is, prefixed with "Original (Page X):", where X is the page number starting from 1.
                      2. Then output the accurate and professional translation prefixed with "Translation (Page X):".
                    - Ensure factual accuracy and preserve the original legal meaning.
                    - Avoid adding, omitting, or altering information.
                    - Separate each page segment with a blank line for clarity.
                    
                    IMPORTANT:
                    - Make sure response WITHOUT any introduction, explanation, or additional description before or after the output.
                    - ONLY output the content in the following strict format.
                    
                    OUTPUT FORMAT:
                    - Clearly label each original page and its translation with page numbers.
                    - Maintain formatting as close to the original as possible.
                    
                    CONTEXT:
                    ```markdown
                    {context}
                    ```
                    """
            elif response_language == "Japanese":
                prompt_text = f"""
                        あなたは契約翻訳を専門とする法律の専門家です。

                        タスク：
                        - 常に事実に基づいた情報を提供し、内容を捏造せず、{response_language} に翻訳してください。
                        - CONTEXT には複数ページの法律文書が含まれます。各ページの冒頭にはページ番号（例："Page 1", "Page 2"...）が記載されています。
                        - 各ページを1つのセグメントとして扱ってください。
                        - 各ページについて：
                          1. 元のページ内容をそのまま出力し、冒頭に "Original (Page X):" と付けること。X は1から始まるページ番号。
                          2. その後、正確かつ専門的な翻訳を "Translation (Page X):" のラベル付きで出力してください。
                        - 事実の正確性を確保し、元の法律的意味を保持してください。
                        - 情報を追加・省略・改変してはいけません。
                        - ページごとに空行で区切ってください。

                        重要事項：
                        - 回答に前置き、説明、追加記述を含めてはいけません。
                        - 以下の厳格なフォーマットに従って出力してください。

                        出力フォーマット：
                        - 各ページの原文と翻訳を明確にページ番号付きでラベル付けすること。
                        - 元のフォーマットを可能な限り保持してください。

                        契約内容：
                        ```markdown
                        {context}
                        ```
                        """
            else:
                prompt_text = f"""
                        你是一名專精於合約翻譯的法律專家。

                        任務：
                        - 你必須始終基於事實提供資訊，絕不捏造內容，並翻譯成 {response_language}。
                        - CONTEXT 可能包含多頁內容，每一頁的開頭會標註頁碼。
                        - 將每一頁視為一個獨立段落。
                        - 對於每一頁：
                          1. 逐字輸出原始頁面內容，並在前方加上 "Original (Page X):"，X 為頁碼（從 1 開始）。
                          2. 接著輸出準確且專業的翻譯，並在前方加上 "Translation (Page X):"。
                        - 確保事實正確並保留原始法律意義。
                        - 避免新增、刪減或修改任何資訊。
                        - 各頁段落之間需以空行分隔，以保持清晰。

                        重要事項：
                        - 回覆中避免包含任何前言、解釋或額外描述。
                        - 僅能依照以下嚴格格式輸出。

                        輸出格式：
                        - 必須清楚標示每頁的原文與翻譯，並附上頁碼。
                        - 保持盡可能接近原始的格式。

                        合約內容：
                        ```markdown
                        {context}
                        ```
                        """
        elif prompt_type == PromptEnum.chat:
            if not message_request:
                raise ValueError("message_request is required for chat prompt type")
            prompt_text = f"""
                    You are a legal expert specializing in contract analysis for business executives.

                    TASK:
                    Given the following legal information or documents, provide concise, accurate, and context-based answers to legal questions.
                    If the information is insufficient, state that clearly.
                    
                    LANGUAGE:
                    - Detect the language used in the USER QUESTION.
                    - Respond in the same language as the USER QUESTION.
                    - If the question is in Chinese, always use traditional chinese.
                    
                    CHAT HISTORY:
                    The following is the past conversation between the user and assistant. Use it as background context to maintain consistency and relevance in the response.
                    {chat_history}
                    
                    CONTEXT:
                    Use this document context as a knowledge source when answering the question.
                    ```markdown
                    {context}
                    ```

                    USER QUESTION:
                    {message_request}
                    
                    RESPONSE INSTRUCTIONS:
                    - Base your answer solely on the CHAT HISTORY and CONTEXT provided.
                    - Make sure response WITHOUT invent any facts.
                    - Be legally accurate and professional.
                    """
        else:
            raise ValueError(f"Unsupported prompt type: {prompt_type}")

        chain = self.model | StrOutputParser()
        try:
            response = await chain.ainvoke(prompt_text)
        except Exception as e:
            logger.error(f"Prompt execution failed: {str(e)}")
            raise
        logger.info(f"Success get {prompt_type} response from AOAI...")
        return response

# - DO NOT write any introduction, explanation, or additional description before or after the output.
