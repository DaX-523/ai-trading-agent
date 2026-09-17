CREATE TYPE "TradingMode" AS ENUM ('SANDBOX', 'TESTNET', 'LIVE');

CREATE TABLE "AppSettings" (
    "id" text PRIMARY KEY,
    "activeMode" "TradingMode" NOT NULL DEFAULT 'SANDBOX'
);

INSERT INTO "AppSettings" ("id", "activeMode") VALUES ('default', 'SANDBOX');

ALTER TABLE "Invocations"
    ADD COLUMN "tradingMode" "TradingMode" NOT NULL DEFAULT 'SANDBOX';

ALTER TABLE "PortfolioSize"
    ADD COLUMN "tradingMode" "TradingMode" NOT NULL DEFAULT 'SANDBOX';

ALTER TABLE "Models"
    ADD COLUMN "testnetLighterApiKey" text,
    ADD COLUMN "testnetAccountIndex" text;

CREATE TABLE "PaperAccounts" (
    "id" text PRIMARY KEY,
    "modelId" text NOT NULL,
    "cashBalance" text NOT NULL,
    "createdAt" timestamp(3) without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" timestamp(3) without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "PaperAccounts_modelId_key" UNIQUE ("modelId"),
    CONSTRAINT "PaperAccounts_modelId_fkey"
        FOREIGN KEY ("modelId") REFERENCES "Models"("id") ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE "PaperPositions" (
    "id" text PRIMARY KEY,
    "modelId" text NOT NULL,
    "symbol" text NOT NULL,
    "side" text NOT NULL,
    "quantity" text NOT NULL,
    "entryPrice" text NOT NULL,
    "marginReserved" text NOT NULL,
    "realizedPnl" text NOT NULL DEFAULT '0',
    "openedAt" timestamp(3) without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "closedAt" timestamp(3) without time zone,
    CONSTRAINT "PaperPositions_modelId_fkey"
        FOREIGN KEY ("modelId") REFERENCES "Models"("id") ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX "PaperAccounts_modelId_idx" ON "PaperAccounts"("modelId");
CREATE INDEX "PaperPositions_modelId_idx" ON "PaperPositions"("modelId");
CREATE INDEX "Invocations_tradingMode_idx" ON "Invocations"("tradingMode");
CREATE INDEX "PortfolioSize_tradingMode_idx" ON "PortfolioSize"("tradingMode");
