export class PriceOracleAdapter {
  async getUsdPrices(tokens: { chainId: string; address: string; symbol: string }[]): Promise<Record<string, number>> {
    // TODO: Implement price fetching from Coingecko or Alchemy Token API
    return {};
  }
} 