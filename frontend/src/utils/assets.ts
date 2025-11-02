export type ChartRange = "24H" | "1W" | "1M" | "1Y" | "ALL";

export interface AssetMeta {
  name: string;
  ticker: string;
  rank?: number;
  watchlistCount?: string;
  marketCap?: number;
  marketCapChange?: number;
  fullyDilutedValuation?: number;
  volume24h?: number;
  volume24hChange?: number;
  totalSupply?: number | null;
  circulatingSupply?: number | null;
  maxSupply?: number | null;
}

const ASSET_METADATA: Record<string, AssetMeta> = {
  BTC: {
    name: "Bitcoin",
    ticker: "BTC",
    rank: 1,
    watchlistCount: "8.1M",
    marketCap: 1_090_000_000_000,
    marketCapChange: 3.12,
    fullyDilutedValuation: 1_140_000_000_000,
    volume24h: 62_500_000_000,
    volume24hChange: -12.4,
    totalSupply: 21_000_000,
    circulatingSupply: 19_750_000,
    maxSupply: 21_000_000,
  },
  ETH: {
    name: "Ethereum",
    ticker: "ETH",
    rank: 2,
    watchlistCount: "3M",
    marketCap: 465_360_000_000,
    marketCapChange: 2.09,
    fullyDilutedValuation: 465_360_000_000,
    volume24h: 36_570_000_000,
    volume24hChange: -16.06,
    totalSupply: 120_690_000,
    circulatingSupply: 120_690_000,
    maxSupply: null,
  },
  BNB: {
    name: "BNB",
    ticker: "BNB",
    rank: 3,
    watchlistCount: "2.3M",
    marketCap: 44_900_000_000,
    marketCapChange: 1.64,
    fullyDilutedValuation: 49_300_000_000,
    volume24h: 1_350_000_000,
    volume24hChange: -9.8,
    totalSupply: 147_000_000,
    circulatingSupply: 145_000_000,
    maxSupply: 200_000_000,
  },
  SOL: {
    name: "Solana",
    ticker: "SOL",
    rank: 5,
    watchlistCount: "1.8M",
    marketCap: 78_600_000_000,
    marketCapChange: 2.32,
    fullyDilutedValuation: 88_200_000_000,
    volume24h: 5_420_000_000,
    volume24hChange: -18.1,
    totalSupply: 580_000_000,
    circulatingSupply: 567_000_000,
    maxSupply: null,
  },
  ADA: {
    name: "Cardano",
    ticker: "ADA",
    rank: 8,
    watchlistCount: "1.4M",
    marketCap: 15_800_000_000,
    marketCapChange: 1.02,
    fullyDilutedValuation: 18_100_000_000,
    volume24h: 780_000_000,
    volume24hChange: -20.5,
    totalSupply: 45_000_000_000,
    circulatingSupply: 35_400_000_000,
    maxSupply: 45_000_000_000,
  },
};

const DEFAULT_METADATA: AssetMeta = {
  name: "Digital Asset",
  ticker: "ASSET",
  watchlistCount: "--",
};

const STABLE_SUFFIXES = ["USDT", "USDC", "BUSD", "USD"]; // Extend as needed

const extractBaseSymbol = (symbol: string) => {
  const upper = symbol.toUpperCase();
  for (const suffix of STABLE_SUFFIXES) {
    if (upper.endsWith(suffix)) {
      return upper.slice(0, upper.length - suffix.length);
    }
  }
  return upper;
};

export const getAssetMeta = (symbol: string): AssetMeta => {
  const base = extractBaseSymbol(symbol);
  return ASSET_METADATA[base] ?? { ...DEFAULT_METADATA, ticker: base, name: base };
};

export const CHART_RANGE_OPTIONS: { value: ChartRange; label: string }[] = [
  { value: "24H", label: "24h" },
  { value: "1W", label: "1W" },
  { value: "1M", label: "1M" },
  { value: "1Y", label: "1Y" },
  { value: "ALL", label: "All" },
];

export const RANGE_TO_TIMEFRAME: Record<ChartRange, string> = {
  "24H": "1m",
  "1W": "5m",
  "1M": "15m",
  "1Y": "1h",
  "ALL": "1d",
};

export const RANGE_TO_DURATION_MS: Partial<Record<ChartRange, number>> = {
  "24H": 24 * 60 * 60 * 1000,
  "1W": 7 * 24 * 60 * 60 * 1000,
  "1M": 30 * 24 * 60 * 60 * 1000,
  "1Y": 365 * 24 * 60 * 60 * 1000,
  // "ALL" intentionally left undefined to request full history
};
