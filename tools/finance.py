import httpx
from infrastructure.logger import logger

async def convert_currency(amount: float, from_curr: str, to_curr: str) -> str:
    """Converts an amount from one fiat/crypto currency to another."""
    # The API strictly requires lowercase codes
    from_curr = from_curr.lower()
    to_curr = to_curr.lower()
    
    url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{from_curr}.json"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            if res.status_code == 404:
                return f"Error: Currency code '{from_curr.upper()}' is not supported."
            res.raise_for_status()
            
            data = res.json()
            rates = data.get(from_curr, {})
            
            if to_curr not in rates:
                return f"Error: Target currency '{to_curr.upper()}' is not supported."
                
            rate = rates[to_curr]
            converted = amount * rate
            
            # Smart formatting: Show more decimals for small crypto values, 2 decimals for normal fiat
            if converted < 0.01:
                formatted_amount = f"{converted:.6f}"
            else:
                formatted_amount = f"{converted:,.2f}"
                
            return f"💱 Conversion:\n{amount:,.2f} {from_curr.upper()} = {formatted_amount} {to_curr.upper()} (Rate: {rate})"
            
        except Exception as e:
            logger.error(f"Currency API Error: {e}")
            return "Currency conversion service is currently offline."

async def get_live_crypto_price(symbol: str) -> str:
    """Gets the real-time cryptocurrency price from Binance."""
    symbol = symbol.upper()
    url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            if res.status_code == 400:
                return f"Error: Invalid trading pair '{symbol}'. Ensure it combines two tickers (e.g., 'BTCUSDT')."
            res.raise_for_status()
            
            data = res.json()
            price = float(data['price'])
            
            # Format with commas for readability
            return f"📈 Binance Live Price:\n{symbol}: {price:,.2f}"
            
        except Exception as e:
            logger.error(f"Binance API Error: {e}")
            return "Crypto pricing service is currently offline."
