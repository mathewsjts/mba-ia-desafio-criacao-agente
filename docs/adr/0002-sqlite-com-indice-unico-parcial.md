# SQLite com reserva cancelada mantida e índice único parcial

Reservas e autorizações de visita ficam em `var/condominio.db`, e as sessões do ADK em `var/sessoes.db`, ambas em SQLite, sem serviço externo. Cancelar uma reserva muda seu status para `cancelada` em vez de apagá-la. Assim a chave primária em `codigo` cobre todos os códigos já emitidos e nenhum código se repete. A exclusividade de área por data é garantida por `UNIQUE (area, data) WHERE status = 'ativa'`: a segunda gravação concorrente falha com `IntegrityError` no instante do `INSERT`, e a tool a traduz numa resposta normal de "data indisponível".

## Considered Options

- **Postgres em container**: daria a mesma garantia com constraint de exclusão, mas exige um serviço extra para o avaliador subir.
- **Conferir a agenda e depois gravar**: não resolve, porque outra reserva pode entrar entre a conferência e a gravação.
- **Apagar a reserva cancelada**: obrigaria a manter uma lista à parte de códigos já usados.
