import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

class Dashboard:
    def __init__(self):
        self.colors = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e', 
            'success': '#2ca02c',
            'danger': '#d62728',
            'warning': '#ff9800',
            'info': '#17a2b8'
        }
    
    def render_connection_status(self, connected: bool, balance: float = 0.0):
        """Render connection status indicators"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if connected:
                st.success("🟢 Conectado")
            else:
                st.error("🔴 Desconectado")
        
        with col2:
            if connected:
                st.metric("💰 Saldo", f"${balance:.2f}")
            else:
                st.metric("💰 Saldo", "N/A")
        
        with col3:
            server_status = "🟢 Online" if connected else "🔴 Offline"
            st.metric("🖥️ Servidor", server_status)
    
    def render_trading_stats(self, stats: dict):
        """Render trading statistics"""
        col1, col2, col3, col4 = st.columns(4)
        
        win_rate = 0.0
        if stats['total'] > 0:
            win_rate = (stats['wins'] / stats['total']) * 100
        
        with col1:
            st.metric(
                "📊 Total de Operações", 
                str(stats['total']),
                delta=None
            )
        
        with col2:
            st.metric(
                "✅ Vitórias", 
                str(stats['wins']),
                delta=None
            )
        
        with col3:
            st.metric(
                "❌ Derrotas", 
                str(stats['losses']),
                delta=None
            )
        
        with col4:
            color = "normal"
            if win_rate >= 70:
                color = "normal"  # Green
            elif win_rate >= 60:
                color = "normal"  # Yellow
            else:
                color = "inverse"  # Red
            
            st.metric(
                "🎯 Taxa de Acerto", 
                f"{win_rate:.1f}%",
                delta=None
            )
    
    def render_candlestick_chart(self, candles: list, asset_name: str = "Asset"):
        """Render candlestick chart with pattern indicators"""
        if not candles or len(candles) == 0:
            st.info("📊 Aguardando dados de velas...")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Create candlestick chart
        fig = go.Figure()
        
        # Add candlesticks
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=asset_name,
            increasing_line_color='#2ca02c',
            decreasing_line_color='#d62728'
        ))
        
        # Highlight potential patterns (last 5 candles)
        if len(df) >= 5:
            last_5 = df.tail(5)
            
            # Check if last 5 candles are same color
            colors = []
            for _, candle in last_5.iterrows():
                if candle['close'] > candle['open']:
                    colors.append('green')
                elif candle['close'] < candle['open']:
                    colors.append('red')
                else:
                    colors.append('neutral')
            
            if len(set(colors)) == 1 and colors[0] != 'neutral':
                # Add pattern highlight
                pattern_color = '#ffeb3b' if colors[0] == 'green' else '#ff5722'
                
                for _, candle in last_5.iterrows():
                    fig.add_vrect(
                        x0=candle['timestamp'] - timedelta(seconds=30),
                        x1=candle['timestamp'] + timedelta(seconds=30),
                        fillcolor=pattern_color,
                        opacity=0.2,
                        layer="below",
                        line_width=0,
                    )
        
        # Update layout
        fig.update_layout(
            title=f"{asset_name} - Análise de Velas",
            xaxis_title="Tempo",
            yaxis_title="Preço",
            height=500,
            showlegend=False,
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_pattern_analysis(self, pattern_detected: bool, pattern_type: str = None, 
                              confidence: float = 0.0):
        """Render pattern analysis section"""
        st.subheader("🔍 Análise de Padrão")
        
        if pattern_detected:
            col1, col2 = st.columns(2)
            
            with col1:
                pattern_display = "5 Velas Verdes" if pattern_type == "5_green" else "5 Velas Vermelhas"
                st.success(f"✅ Padrão Detectado: {pattern_display}")
            
            with col2:
                confidence_color = "🟢" if confidence >= 80 else "🟡" if confidence >= 60 else "🔴"
                st.metric("🎯 Confiança", f"{confidence_color} {confidence:.1f}%")
            
            # Trade recommendation
            direction = "PUT (Baixa)" if pattern_type == "5_green" else "CALL (Alta)"
            st.info(f"📈 Recomendação: {direction}")
            
        else:
            st.info("👀 Monitorando padrões... Nenhum detectado no momento.")
    
    def render_backtest_results(self, backtest_results: dict):
        """Render backtest results"""
        st.subheader("📊 Resultados do Backtest")
        
        if not backtest_results or backtest_results.get('total_trades', 0) == 0:
            st.warning("⚠️ Backtest não executado ou sem dados suficientes.")
            return
        
        # Main metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Operações Testadas", backtest_results['total_trades'])
        
        with col2:
            win_rate = backtest_results['win_rate']
            st.metric("🎯 Taxa de Acerto", f"{win_rate:.1f}%")
        
        with col3:
            approved = "✅ Aprovado" if win_rate >= 60 else "❌ Reprovado"
            st.metric("✔️ Status", approved)
        
        # Detailed results
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Resultados Financeiros:**")
            st.write(f"- Lucro/Prejuízo: ${backtest_results.get('profit_loss', 0):.2f}")
            st.write(f"- Saldo Final: ${backtest_results.get('final_balance', 0):.2f}")
            st.write(f"- Drawdown Máximo: {backtest_results.get('max_drawdown', 0):.1f}%")
        
        with col2:
            st.write("**Performance:**")
            st.write(f"- Trades Vencedores: {backtest_results.get('winning_trades', 0)}")
            st.write(f"- Trades Perdedores: {backtest_results.get('losing_trades', 0)}")
            st.write(f"- Sharpe Ratio: {backtest_results.get('sharpe_ratio', 0):.3f}")
        
        # Visual representation
        if backtest_results['total_trades'] > 0:
            wins = backtest_results['winning_trades']
            losses = backtest_results['losing_trades']
            
            fig = px.pie(
                values=[wins, losses],
                names=['Vitórias', 'Derrotas'],
                title="Distribuição de Resultados",
                color_discrete_map={'Vitórias': '#2ca02c', 'Derrotas': '#d62728'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def render_trades_history(self, trades: list):
        """Render trades history table"""
        st.subheader("📋 Histórico de Operações")
        
        if not trades or len(trades) == 0:
            st.info("📝 Nenhuma operação realizada ainda.")
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(trades)
        
        # Format timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M:%S')
        
        # Select relevant columns
        display_columns = ['timestamp', 'asset', 'direction', 'amount', 'pattern']
        if 'status' in df.columns:
            display_columns.append('status')
        
        # Display table
        st.dataframe(
            df[display_columns].tail(10),  # Show last 10 trades
            hide_index=True,
            use_container_width=True
        )
        
        # Summary stats
        if len(trades) > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_amount = sum(trade.get('amount', 0) for trade in trades)
                st.metric("💰 Volume Total", f"${total_amount:.2f}")
            
            with col2:
                avg_amount = total_amount / len(trades) if trades else 0
                st.metric("📊 Valor Médio", f"${avg_amount:.2f}")
            
            with col3:
                st.metric("📈 Total de Operações", len(trades))
    
    def render_market_analysis(self, market_data: dict):
        """Render market analysis section"""
        st.subheader("📊 Análise de Mercado")
        
        if not market_data:
            st.info("📊 Analisando condições de mercado...")
            return
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend = market_data.get('trend', 'unknown')
            trend_emoji = {
                'bullish': '📈',
                'bearish': '📉', 
                'sideways': '↔️'
            }.get(trend, '❓')
            
            st.metric("📊 Tendência", f"{trend_emoji} {trend.title()}")
        
        with col2:
            volatility = market_data.get('volatility', 'unknown')
            vol_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(volatility, '❓')
            
            st.metric("⚡ Volatilidade", f"{vol_emoji} {volatility.title()}")
        
        with col3:
            strength = market_data.get('strength', 0)
            st.metric("💪 Força da Tendência", f"{strength:.1f}%")
    
    def render_risk_management(self, balance: float, suggested_amount: float):
        """Render risk management information"""
        st.subheader("⚠️ Gestão de Risco")
        
        risk_percentage = (suggested_amount / balance * 100) if balance > 0 else 0
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("💰 Saldo Atual", f"${balance:.2f}")
            st.metric("💵 Valor Sugerido", f"${suggested_amount:.2f}")
        
        with col2:
            st.metric("📊 Risco por Trade", f"{risk_percentage:.1f}%")
            
            if risk_percentage <= 2:
                st.success("✅ Risco Baixo")
            elif risk_percentage <= 5:
                st.warning("⚠️ Risco Moderado")
            else:
                st.error("🚨 Risco Alto")
        
        # Risk guidelines
        st.info("""
        **Diretrizes de Risco:**
        - 📊 Máximo 2% do saldo por operação
        - 🎯 Opere apenas com backtest aprovado (>60%)
        - ⏰ Evite overtrading - qualidade > quantidade
        - 📈 Mantenha registro de todas as operações
        """)
    
    def render_system_alerts(self, alerts: list = None):
        """Render system alerts and notifications"""
        if not alerts:
            alerts = []
        
        if alerts:
            st.subheader("🚨 Alertas do Sistema")
            
            for alert in alerts:
                alert_type = alert.get('type', 'info')
                message = alert.get('message', '')
                timestamp = alert.get('timestamp', datetime.now())
                
                if alert_type == 'error':
                    st.error(f"🚨 {message} - {timestamp.strftime('%H:%M:%S')}")
                elif alert_type == 'warning':
                    st.warning(f"⚠️ {message} - {timestamp.strftime('%H:%M:%S')}")
                elif alert_type == 'success':
                    st.success(f"✅ {message} - {timestamp.strftime('%H:%M:%S')}")
                else:
                    st.info(f"ℹ️ {message} - {timestamp.strftime('%H:%M:%S')}")

# Example usage for testing
if __name__ == "__main__":
    dashboard = Dashboard()
    
    # Test with sample data
    st.title("Dashboard Test")
    
    # Connection status
    dashboard.render_connection_status(True, 1250.50)
    
    # Trading stats
    sample_stats = {'total': 15, 'wins': 10, 'losses': 5}
    dashboard.render_trading_stats(sample_stats)
    
    # Sample backtest results
    sample_backtest = {
        'total_trades': 25,
        'winning_trades': 18,
        'losing_trades': 7,
        'win_rate': 72.0,
        'profit_loss': 145.50,
        'final_balance': 1145.50,
        'max_drawdown': 8.5,
        'sharpe_ratio': 1.25
    }
    
    dashboard.render_backtest_results(sample_backtest)
