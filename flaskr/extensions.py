from adapters.in_memory.bank_repository import InMemoryBankRepository
from adapters.in_memory.user_repository import InMemoryUserRepository
from adapters.sqllite.bank_repository import SqlliteBankRepository
from adapters.sqllite.user_repository import SqlliteUserRepository
from core.ports.bank_repository import BankRepository
from core.ports.user_repository import UserRepository
from instance.config import ADAPTER

user_repository: UserRepository = {
    "sqllite": SqlliteUserRepository,
    "in_memory": InMemoryUserRepository,
}.get(ADAPTER, SqlliteUserRepository)()

bank_repository: BankRepository = {
    "sqllite": SqlliteBankRepository,
    "in_memory": InMemoryBankRepository,
}.get(ADAPTER, SqlliteUserRepository)()
