import { cn } from '@/lib/utils';

interface AssetLogoProps {
  symbol: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const SIZE_MAP = {
  sm: 'h-6 w-6',
  md: 'h-10 w-10',
  lg: 'h-12 w-12',
  xl: 'h-16 w-16',
};

const LOGO_COLORS: Record<string, { bg: string; text: string }> = {
  BTC: { bg: 'from-orange-500 to-orange-600', text: '₿' },
  ETH: { bg: 'from-blue-500 to-indigo-600', text: 'Ξ' },
  BNB: { bg: 'from-yellow-400 to-yellow-500', text: 'B' },
  SOL: { bg: 'from-purple-500 to-purple-600', text: 'S' },
  ADA: { bg: 'from-cyan-500 to-blue-500', text: '₳' },
};

const extractBase = (symbol: string) => {
  const upper = symbol.toUpperCase();
  return (
    ['USDT', 'USDC', 'BUSD', 'USD']
      .map(suffix => (upper.endsWith(suffix) ? upper.slice(0, -suffix.length) : null))
      .find(Boolean) || upper
  );
};

export const AssetLogo = ({ symbol, size = 'md', className }: AssetLogoProps) => {
  const base = extractBase(symbol);
  const config = LOGO_COLORS[base] || {
    bg: 'from-slate-600 to-slate-700',
    text: base.slice(0, 1),
  };

  return (
    <div
      className={cn(
        'rounded-full bg-gradient-to-br flex items-center justify-center font-bold text-white shadow-lg ring-2 ring-slate-800/50',
        config.bg,
        SIZE_MAP[size],
        className
      )}
    >
      {config.text}
    </div>
  );
};
