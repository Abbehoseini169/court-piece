# Court Piece — realtidsserver (steg 1)

Det här är "domaren": en server som äger spelet och låter fyra spelare
(människor och/eller AI) spela Court Piece mot varandra i realtid. Det här
steget innehåller bara servern. Klienten (det man ser i webbläsaren) bygger
vi i nästa steg.

## Vad du behöver först

Installera **Node.js** (LTS-versionen) från https://nodejs.org
Det ger dig både `node` och `npm`. Du behöver inget mer.

Kontrollera att det funkar — öppna en terminal och skriv:

    node --version
    npm --version

Om båda skriver ut ett versionsnummer är du redo.

## Så här kör du servern

1. Öppna en terminal och gå till server-mappen:

       cd court-piece/server

2. Installera biblioteken (Express + Socket.IO). Detta görs en gång:

       npm install

3. Starta servern:

       npm start

   Du ska se: `Court Piece-servern (domaren) lyssnar på port 3001`
   Servern körs nu. Lämna terminalen öppen.

## Så här testar du att allt fungerar (utan klient ännu)

Öppna en NY terminal (låt servern fortsätta köra i den första) och kör:

    cd court-piece/server
    node smoke-test.js

Det ansluter en testklient, skapar ett rum, fyller på med 3 AI-spelare och
spelar en hel hand. Du ser korten läggas ut stick för stick och poängen i
slutet. Det bevisar att servern och spelreglerna hänger ihop.

## Filerna och vad de gör

- **game.js** — de rena spelreglerna (kortlek, blandning, vem som vinner
  sticket, AI-besluten, poäng). Inget om nätverk eller skärmar. Det här är
  samma logik som i den ursprungliga app-prototypen, och kan återanvändas
  rakt av i en framtida mobilapp.

- **server.js** — domaren. Hanterar rum (skapa/gå med via 4-teckenskod),
  30-sekunders nedräkning innan tomma platser fylls med AI, tar emot drag
  från spelare, validerar dem mot reglerna, och skickar tillbaka det nya
  speltillståndet till alla. Skickar ALDRIG en spelares kort till någon
  annan — det är så fusk förhindras.

- **smoke-test.js** — ett litet testskript (ingen webbläsare) som spelar en
  hand automatiskt, så du snabbt kan se att servern lever.

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
