# Residencial Aurora

O condomínio atendido pelo assistente virtual: moradores reservam áreas comuns, autorizam visitas e tiram dúvidas sobre o regulamento interno.

## Pessoas e unidades

**Apartamento**:
A unidade autônoma do condomínio, identificada pelo número (ex.: "101"). É a quem pertencem reservas e autorizações de visita.
_Avoid_: Unidade, usuário, conta

**Morador**:
A pessoa autenticada que fala com o assistente em nome de um apartamento.
_Avoid_: Usuário, cliente, condômino

**Visitante**:
A pessoa de fora do condomínio nomeada numa autorização de visita.
_Avoid_: Convidado

## Áreas e reservas

**Área comum**:
Espaço compartilhado que pode ser reservado (salão de festas, churrasqueira, quadra), com uma taxa associada.
_Avoid_: Espaço, ambiente

**Taxa**:
O valor em reais associado a uma área comum. Taxa zero significa área sem cobrança.
_Avoid_: Preço, tarifa

**Reserva**:
O direito de um apartamento usar uma área comum numa data. Uma reserva está ativa ou cancelada; cada área tem no máximo uma reserva ativa por data.
_Avoid_: Agendamento, booking

**Código de reserva**:
O identificador de uma reserva, gerado pelo sistema e nunca reutilizado, nem o de uma reserva cancelada.
_Avoid_: ID, protocolo

**Cobrança**:
A marca de que uma reserva de área com taxa maior que zero gera custo para o apartamento. Não envolve pagamento.
_Avoid_: Pagamento, fatura

**Disponibilidade**:
Se uma área está livre ou ocupada numa data, sem revelar de quem é a reserva.
_Avoid_: Agenda (quando significar ver os donos das reservas)

## Visitas

**Autorização de visita**:
O registro que libera a entrada de um visitante no prédio numa data, em nome de um apartamento.
_Avoid_: Visitante (para o registro), liberação, acesso

## Conversa

**Sessão**:
Uma conversa do morador com o assistente, vinculada a um único apartamento definido na criação.
_Avoid_: Chat, conversa (como termo técnico)

**Confirmação pendente**:
Uma ação que gera cobrança ou cria uma autorização de visita e que aguarda o morador aprovar ou negar pela rota de confirmações.
_Avoid_: Pendência, aprovação

**Regulamento**:
O regulamento interno do condomínio, dividido em capítulos por assunto.
_Avoid_: Regimento, normas

**Capítulo**:
Uma divisão do regulamento que trata de um único assunto (ex.: Capítulo IV: Piscina).
_Avoid_: Seção
