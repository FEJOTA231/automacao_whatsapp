Feature: Enviar mensagem no WhatsApp Web
  Scenario: Enviar a mensagem "teste" para meu contato
    Given que o WhatsApp Web está aberto
    When eu procurar pelo grupo "Teste"     
    And eu enviar a mensagem "teste"
    Then a mensagem deve ser enviada com sucesso
