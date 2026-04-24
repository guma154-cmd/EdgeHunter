"""
EdgeHunter — Bankroll Manager
Rastreia saldos estimados por casa e emite alertas de banca baixa.
"""
import logging

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
            cls._instance.balances = {
                'bet365':  20.0,
                'betano':  20.0,
                'betfair': 20.0,
                'pinnacle': 20.0
            }
        return cls._instance
    
    def update(self, bookmaker: str, amount: float):
        """
        Atualiza saldo após aposta (amount negativo)
        ou liquidação (amount positivo).
        """
        book = bookmaker.lower()
        if book in self.balances:
            self.balances[book] += amount
            self._check_low_balance(book)
    
    def can_cover(self, bookmaker_A: str, stake_A: float,
                  bookmaker_B: str, stake_B: float) -> bool:
        """Verifica se tem saldo para cobrir os dois lados."""
        return (
            self.balances.get(bookmaker_A.lower(), 0) >= stake_A and
            self.balances.get(bookmaker_B.lower(), 0) >= stake_B
        )
    
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
        with app.app_context():
            from app.models import Surebet
            # Reset para valor inicial padrão
            for book in self.balances:
                self.balances[book] = 20.0
                
            # Buscar todas as surebets (arbitragem)
            # Nota: Aqui simplificamos considerando apenas a redução por stake.
            # Em um sistema real, monitoraríamos a liquidação para somar os ganhos.
            all_surebets = Surebet.query.all()
            for s in all_surebets:
                self.balances[s.bookmaker_A.lower()] -= s.stake_A
                self.balances[s.bookmaker_B.lower()] -= s.stake_B
                
                # Se estiver liquidado, somar o retorno garantido (simplificado)
                if s.status == 'settled':
                    # O retorno vai para um dos lados dependendo do resultado real,
                    # mas para o "saldo total do sistema" o lucro é adicionado.
                    # Aqui apenas deduzimos as stakes para controle de fluxo.
                    pass
