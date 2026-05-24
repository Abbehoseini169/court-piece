# Court Piece — realtidsserver (steg 1)

Det här är "domaren": en server som äger spelet och låter fyra spelare
(människor och/eller AI) spela Court Piece mot varandra i realtid. Det här
steget innehåller bara servern. Klienten (det man ser i webbläsaren) bygger
vi i nästa steg.

## Vad du behöver först

Installera **Python 3.10+** om du inte redan har det: https://www.python.org

Kontrollera att det funkar — öppna en terminal och skriv:

    python3 --version

Om det skriver ut ett versionsnummer (t.ex. `Python 3.11.4`) är du redo.

## Så här kör du servern

1. Öppna en terminal och gå till projektmappen:

       cd court-piece

2. Installera biblioteken (Flask + Socket.IO). Detta görs en gång:

       pip install -r requirements.txt

3. Starta servern:

       python server.py

   Du ska se: `Court Piece-servern (Python) lyssnar på port 3001`
   Servern körs nu. Lämna terminalen öppen.

## Så här testar du att allt fungerar (utan klient ännu)

Öppna en NY terminal (låt servern fortsätta köra i den första) och kör:

    cd court-piece
    python smoke-test.py

Det ansluter en testklient, skapar ett rum, fyller på med 3 AI-spelare och
spelar en hel match. Du ser korten läggas ut stick för stick och poängen i
slutet. Det bevisar att servern och spelreglerna hänger ihop.

## Filerna och vad de gör

- **game.py** — de rena spelreglerna (kortlek, blandning, vem som vinner
  sticket, AI-besluten, poäng). Inget om nätverk eller skärmar.

- **server.py** — domaren. Hanterar rum (skapa/gå med via 4-teckenskod),
  30-sekunders nedräkning innan tomma platser fylls med AI, tar emot drag
  från spelare, validerar dem mot reglerna, och skickar tillbaka det nya
  speltillståndet till alla. Skickar ALDRIG en spelares kort till någon
  annan — det är så fusk förhindras.

- **smoke-test.py** — ett litet testskript (ingen webbläsare) som spelar en
  match automatiskt, så du snabbt kan se att servern lever.

## Så startas ett spel (båda sätten finns)

- **Rumskod:** en spelare skapar ett rum och får en 4-teckenskod (t.ex.
  `QTK2`). Tre kompisar går med via koden.
- **Auto-ifyllning:** om rummet inte fyllts med 4 personer inom 30 sekunder
  fylls de tomma platserna med AI och spelet börjar automatiskt. Värden kan
  också trycka "starta tidigt".
- Fylls alla fyra platser av människor innan tiden gått, startar spelet
  direkt.

(Matchmaking — att para ihop främlingar automatiskt — är medvetet utelämnat
i det här första steget. Det läggs till som ett separat steg senare.)

## Nästa steg

Klienten: ett Vite + React-projekt i webbläsaren som visar dina kort,
låter dig klicka för att spela, och visar de andra spelarnas drag i realtid
via samma Socket.IO-kanal som testskriptet använder.
