"""
EdgeHunter — Bankroll Manager
Rastreia saldos estimados por casa e emite alertas de banca baixa.
"""
import logging
import os

BANKROLL_MIN_ALERT = 10.0  # alerta se banca < R$10

class BankrollManager:
    """
    Rastreia saldo estimado por casa.
    Alerta quando banca está baixa para cobrir surebet.
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BankrollManager, cls).__new__(cls)
            initial = float(os.getenv('INITIAL_BANKROLL_PER_BOOK', '50.0'))
            cls._instance.balances = {
                'bet365':  initial,
                'betano':  initial,
                'betfair': initial,
                'pinnacle': initial,
                'superbet': initial
            }
        return cls._instance
    
    def update(self, bookmaker: str, amount: float):
        """
        Atualiza saldo após aposta (amount negativo)
        ou liquidação (amount positivo).
        """
        if not bookmaker: return
        book = bookmaker.lower()
        if book in self.balances:
            self.balances[book] += amount
            self._check_low_balance(book)
        else:
            # Se a casa não existe no dict, inicializa ela
            initial = float(os.getenv('INITIAL_BANKROLL_PER_BOOK', '50.0'))
            self.balances[book] = initial + amount
    
    def can_cover(self, book_A: str, stake_A: float,
                  book_B: str, stake_B: float,
                  book_X: str = None, stake_X: float = 0.0) -> bool:
        """Verifica se tem saldo para cobrir todos os lados (2 ou 3)."""
        ok = (
            self.balances.get(book_A.lower(), 0) >= stake_A and
            self.balances.get(book_B.lower(), 0) >= stake_B
        )
        if ok and book_X:
            ok = self.balances.get(book_X.lower(), 0) >= stake_X
        return ok
    
    def _check_low_balance(self, bookmaker: str):
        """Alerta Telegram se saldo estiver baixo."""
        balance = self.balances[bookmaker]
        if balance < BANKROLL_MIN_ALERT:
            from app.alerts.telegram_bot import send_message
            send_message(
                f"⚠️ *Banca Baixa — {bookmaker.upper()}*\n"
                f"Saldo estimado: R$ {balance:.2f}\n"
                f"Mínimo recomendado: R$ {BANKROLL_MIN_ALERT:.2f}\n"
                f"💡 Considere recarregar antes da próxima entrada."
            )
    
    def get_status(self) -> str:
        """Retorna status da banca para o heartbeat."""
        lines = []
        for book, balance in self.balances.items():
            status = "✅" if balance >= BANKROLL_MIN_ALERT else "⚠️"
            lines.append(f"{status} {book}: R$ {balance:.2f}")
        return "\n".join(lines)
    
    def load_from_db(self, app):
        """Recalcula saldos com base nas apostas registradas."""
        initial = float(os.getenv('INITIAL_BANKROLL_PER_BOOK', '50.0'))
        with app.app_context():
            from app.models import Surebet
            # Reset para valor inicial padrão
            for book in self.balances:
                self.balances[book] = initial
                
            all_surebets = Surebet.query.all()
            for s in all_surebets:
                if s.bookmaker_A.lower() in self.balances:
                    self.balances[s.bookmaker_A.lower()] -= s.stake_A
                if s.bookmaker_B.lower() in self.balances:
                    self.balances[s.bookmaker_B.lower()] -= s.stake_B
                if s.bookmaker_X and s.bookmaker_X.lower() in self.balances:
                    self.balances[s.bookmaker_X.lower()] -= s.stake_X
                
                # Se estiver liquidado, somar o retorno garantido (simplificado)
                if s.status == 'settled':
                    # Simplificação: dividimos o lucro entre as casas para manter o saldo total
                    # Em um sistema real, o lucro iria para a casa ganhadora.
                    n_books = 3 if s.bookmaker_X else 2
                    share = s.guaranteed_profit / n_books
                    self.balances[s.bookmaker_A.lower()] += (s.stake_A + share)
                    self.balances[s.bookmaker_B.lower()] += (s.stake_B + share)
                    if s.bookmaker_X:
                        self.balances[s.bookmaker_X.lower()] += (s.stake_X + share)

