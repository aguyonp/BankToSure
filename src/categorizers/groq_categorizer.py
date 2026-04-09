import time
import json
import urllib.parse
import requests
from loguru import logger

from ..config import settings

class GroqCategorizer:
    """AI-powered categorizer using Groq & Llama-3.3-70B."""

    def __init__(self):
        self.sure_api_url = f"{settings.sure_url}/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": settings.sure_api_key.get_secret_value(),
            "Content-Type": "application/json"
        })
        self.groq_api_key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else None

    def get_categories(self) -> dict:
        res = self.session.get(f"{self.sure_api_url}/categories")
        if res.status_code != 200:
            logger.error(f"Error fetching categories: {res.text}")
            return {}
        return {c['id']: c['name'] for c in res.json().get('categories', [])}

    def get_uncategorized_transactions(self) -> list:
        logger.debug("Fetching new uncategorized transactions...")
        res = self.session.get(f"{self.sure_api_url}/transactions?per_page=100")
        if res.status_code != 200:
            return []
            
        total_pages = res.json().get('pagination', {}).get('total_pages', 1)
        uncategorized = []
        
        for page in range(1, total_pages + 1):
            page_res = self.session.get(f"{self.sure_api_url}/transactions?per_page=100&page={page}")
            for tx in page_res.json().get('transactions', []):
                if not tx.get('category'):
                    uncategorized.append(tx)
        return uncategorized

    def get_similar_transactions_history(self, tx_name: str) -> str:
        words = [w for w in tx_name.split() if len(w) > 3 and not "/" in w]
        search_term = " ".join(words[:2]) if words else tx_name
        
        query = urllib.parse.quote(search_term)
        res = self.session.get(f"{self.sure_api_url}/transactions?search={query}&per_page=5")
        
        history_lines = []
        if res.status_code == 200:
            for t in res.json().get('transactions', []):
                if t.get('category') and t['category']['name'] != settings.category_to_verify:
                    cat_name = t['category']['name']
                    history_lines.append(f"- L'achat '{t['name']}' avait été classé dans '{cat_name}'")
        
        unique_history = list(set(history_lines))
        return "\n".join(unique_history) if unique_history else "Aucun historique pertinent trouvé."

    def ask_groq(self, tx_name: str, amount: float, numbered_cats: dict, history_context: str) -> dict:
        cats_text = "\n".join([f"{num}: {data['name']}" for num, data in numbered_cats.items()])
        
        prompt = f"""
        Tu es un expert financier spécialisé dans les banques françaises. 
        Analyse cette transaction :
        
        Nom: {tx_name}
        Montant: {amount} €
        
        Voici les catégories disponibles :
        {cats_text}
        
        HISTORIQUE DE L'UTILISATEUR (Pour t'aider à déduire) :
        {history_context}
        
        ANTISÈCHE FRANÇAISE :
        - "Flitter", "Macif", "Alan", "Direct Assurance" -> Assurances (Insurance).
        - "VIR INST virement vers...", "virement compte à compte" ou prénom/nom -> Transfers. 
          ATTENTION : Si le virement contient le mot "PEA" ou "Bourse", choisis "Savings & Investments".
        - "WERO", "Lydia", "Paylib" -> Remboursement entre amis.
        - Supermarchés (Leclerc, Carrefour, Auchan, Grand Frais...) -> Groceries.
        
        RÉPONSE ATTENDUE EN JSON STRICTEMENT :
        - "category_number": le chiffre exact (en string) de la catégorie choisie.
        - "confidence": un entier de 0 à 100 indiquant ta certitude. (Mets moins de {settings.confidence_threshold} si le nom est obscur).
        
        Exemple :
        {{"category_number": "3", "confidence": 95}}
        """
        
        headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0 
        }
        
        try:
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            if res.status_code != 200:
                logger.warning(f"Erreur API Groq : {res.text}")
                return None
            return json.loads(res.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"Erreur traitement IA : {e}")
            return None

    def update_category(self, tx_id: str, category_id: str) -> bool:
        payload = {"transaction": {"category_id": category_id}}
        res = self.session.patch(f"{self.sure_api_url}/transactions/{tx_id}", json=payload)
        return res.status_code == 200

    def run(self) -> int:
        if not self.groq_api_key:
            logger.warning("GROQ_API_KEY is missing. Skipping auto-categorization.")
            return 0

        logger.info("Starting AI Categorization...")
        raw_cats = self.get_categories()
        if not raw_cats: return 0

        numbered_cats = {str(i): {"id": c_id, "name": name} for i, (c_id, name) in enumerate(raw_cats.items(), 1)}
        
        to_verify_num = None
        for num, data in numbered_cats.items():
            if data['name'].lower() == settings.category_to_verify.lower():
                to_verify_num = num
                break
        
        if not to_verify_num:
            logger.warning(f"Fallback category '{settings.category_to_verify}' not found in Sure!")

        transactions = self.get_uncategorized_transactions()
        if not transactions:
            logger.info("No uncategorized transactions found.")
            return 0
            
        logger.info(f"Found {len(transactions)} transaction(s) to categorize.")
        
        success_count = 0
        for tx in transactions:
            tx_id, tx_name, tx_amount = tx['id'], tx['name'], tx['amount']
            logger.debug(f"Analyzing: {tx_name} ({tx_amount} €)")
            
            history = self.get_similar_transactions_history(tx_name)
            if history != "Aucun historique pertinent trouvé.":
                logger.debug(f"RAG Context found for '{tx_name}'")
                
            ai_response = self.ask_groq(tx_name, tx_amount, numbered_cats, history)
            if not ai_response:
                time.sleep(3)
                continue
                
            predicted_num = ai_response.get("category_number")
            try:
                confidence = int(ai_response.get("confidence", 0))
            except (ValueError, TypeError):
                confidence = 0
            
            if predicted_num is not None:
                predicted_num = str(predicted_num)
            
            if confidence < settings.confidence_threshold and to_verify_num:
                logger.debug(f"Low confidence ({confidence}%). Routing to '{settings.category_to_verify}'.")
                predicted_num = to_verify_num

            if predicted_num in numbered_cats:
                real_cat_id = numbered_cats[predicted_num]['id']
                cat_name = numbered_cats[predicted_num]['name']
                
                if self.update_category(tx_id, real_cat_id):
                    logger.success(f"Categorized: '{tx_name}' -> {cat_name} (Confidence: {confidence}%)")
                    success_count += 1
                else:
                    logger.error(f"Failed to update '{tx_name}' in Sure")
            else:
                logger.warning(f"Invalid AI output format for '{tx_name}'")
                
            time.sleep(3) # Respect Groq rate limits
            
        logger.info(f"AI Categorization finished. {success_count}/{len(transactions)} successful.")
        return success_count
