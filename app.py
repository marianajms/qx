import streamlit as st
import asyncio
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os

from quotex_client import QuotexClient
from strategy import TradingStrategy
from backtest import BacktestEngine
from dashboard import Dashboard

# Configure page
st.set_page_config(
    page_title="Quotex Trading Bot - 5 Velas Iguais",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'quotex_client' not in st.session_state:
    st.session_state.quotex_client = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'trading_active' not in st.session_state:
    st.session_state.trading_active = False
if 'trades_history' not in st.session_state:
    st.session_state.trades_history = []
if 'candles_data' not in st.session_state:
    st.session_state.candles_data = {}
if 'selected_asset' not in st.session_state:
    st.session_state.selected_asset = "EURUSD_otc"
if 'strategy_stats' not in st.session_state:
    st.session_state.strategy_stats = {'total': 0, 'wins': 0, 'losses': 0}

def main():
    st.title("🚀 Quotex Trading Bot - Estratégia 5 Velas Iguais")
    
    # Sidebar for connection and settings
    with st.sidebar:
        st.header("🔐 Conexão Quotex")
        
        if not st.session_state.connected:
            email = st.text_input("Email", placeholder="seu-email@exemplo.com")
            password = st.text_input("Senha", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                demo_account = st.checkbox("Conta Demo", value=True)
            with col2:
                connect_btn = st.button("🔌 Conectar", type="primary")
            
            if connect_btn and email and password:
                with st.spinner("Conectando com Quotex..."):
                    try:
                        client = QuotexClient(email, password, demo_account)
                        success = asyncio.run(client.connect())
                        
                        if success:
                            st.session_state.quotex_client = client
                            st.session_state.connected = True
                            st.success("✅ Conectado com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Falha na conexão. Verifique suas credenciais.")
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)}")
        else:
            st.success("✅ Conectado")
            
            # Account info
            if st.session_state.quotex_client:
                balance = asyncio.run(st.session_state.quotex_client.get_balance())
                st.metric("💰 Saldo", f"${balance:.2f}")
            
            if st.button("🔌 Desconectar"):
                if st.session_state.quotex_client:
                    asyncio.run(st.session_state.quotex_client.disconnect())
                st.session_state.connected = False
                st.session_state.quotex_client = None
                st.session_state.trading_active = False
                st.rerun()
        
        st.divider()
        
        # Trading settings
        if st.session_state.connected:
            st.header("⚙️ Configurações")
            
            # Asset selection
            otc_assets = [
                "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc",
                "USDCAD_otc", "NZDUSD_otc", "EURJPY_otc", "GBPJPY_otc"
            ]
            
            st.session_state.selected_asset = st.selectbox(
                "📊 Ativo OTC",
                otc_assets,
                index=otc_assets.index(st.session_state.selected_asset)
            )
            
            trade_amount = st.number_input(
                "💵 Valor da Operação",
                min_value=1.0,
                max_value=10000.0,
                value=10.0,
                step=1.0
            )
            
            expiry_time = st.selectbox(
                "⏰ Tempo de Expiração",
                [60, 120, 180, 300, 600],
                index=0,
                format_func=lambda x: f"{x//60}m {x%60}s" if x >= 60 else f"{x}s"
            )
            
            # Trading controls
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("▶️ Iniciar Bot", type="primary", disabled=st.session_state.trading_active):
                    st.session_state.trading_active = True
                    st.rerun()
            
            with col2:
                if st.button("⏹️ Parar Bot", disabled=not st.session_state.trading_active):
                    st.session_state.trading_active = False
                    st.rerun()

    # Main content area
    if not st.session_state.connected:
        st.info("👆 Conecte-se com sua conta Quotex na barra lateral para começar.")
        
        # Show strategy explanation
        st.header("📚 Como Funciona a Estratégia")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🎯 Estratégia das 5 Velas Iguais")
            st.write("""
            1. **Monitoramento**: O bot monitora velas em tempo real
            2. **Detecção**: Identifica 5 velas consecutivas da mesma cor
            3. **Backtest**: Valida se a estratégia tem >60% de acerto nas últimas 100 velas
            4. **Execução**: Se aprovado no backtest, executa ordem na 6ª vela
            5. **Direção**: Se 5 velas verdes → PUT | Se 5 velas vermelhas → CALL
            """)
        
        with col2:
            st.subheader("⚠️ Avisos Importantes")
            st.write("""
            - ⚠️ **Risco**: Trading envolve risco de perda
            - 🧪 **Teste**: Sempre teste com conta demo primeiro
            - 📊 **Backtest**: Estratégia só executa se taxa de acerto >60%
            - ⏰ **Tempo Real**: Monitora apenas ativos OTC
            - 🔄 **Automático**: Execução completamente automatizada
            """)
            
    else:
        # Trading interface
        dashboard = Dashboard()
        
        # Status indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_color = "🟢" if st.session_state.connected else "🔴"
            st.metric("Status Conexão", f"{status_color} {'Online' if st.session_state.connected else 'Offline'}")
        
        with col2:
            bot_status = "🟢 Ativo" if st.session_state.trading_active else "🔴 Parado"
            st.metric("Status Bot", bot_status)
        
        with col3:
            win_rate = 0
            if st.session_state.strategy_stats['total'] > 0:
                win_rate = (st.session_state.strategy_stats['wins'] / st.session_state.strategy_stats['total']) * 100
            st.metric("Taxa de Acerto", f"{win_rate:.1f}%")
        
        with col4:
            st.metric("Operações Hoje", str(st.session_state.strategy_stats['total']))
        
        st.divider()
        
        # Charts and analysis
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"📊 {st.session_state.selected_asset} - Tempo Real")
            
            # Placeholder for real-time chart
            chart_placeholder = st.empty()
            
            # Get real-time candles if trading is active
            if st.session_state.trading_active and st.session_state.quotex_client:
                try:
                    # Get recent candles
                    candles = asyncio.run(
                        st.session_state.quotex_client.get_candles(
                            st.session_state.selected_asset,
                            100
                        )
                    )
                    
                    if candles and len(candles) > 0:
                        # Convert to DataFrame
                        df = pd.DataFrame(candles)
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        
                        # Create candlestick chart
                        fig = go.Figure(data=go.Candlestick(
                            x=df['timestamp'],
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            name=st.session_state.selected_asset
                        ))
                        
                        fig.update_layout(
                            title=f"{st.session_state.selected_asset} - Últimas 100 Velas",
                            xaxis_title="Tempo",
                            yaxis_title="Preço",
                            height=400
                        )
                        
                        chart_placeholder.plotly_chart(fig, use_container_width=True)
                        
                        # Strategy analysis
                        strategy = TradingStrategy()
                        pattern_detected, pattern_type, confidence = strategy.detect_pattern(candles[-6:])
                        
                        if pattern_detected:
                            st.success(f"🎯 Padrão detectado: {pattern_type} (Confiança: {confidence:.1f}%)")
                            
                            # Run backtest
                            backtest = BacktestEngine()
                            backtest_result = backtest.run_backtest(candles[-100:], strategy)
                            
                            if backtest_result['win_rate'] >= 60:
                                st.success(f"✅ Backtest aprovado: {backtest_result['win_rate']:.1f}% de acerto")
                                
                                # Execute trade if active
                                if st.session_state.trading_active:
                                    direction = "put" if pattern_type == "5_green" else "call"
                                    
                                    with st.spinner("Executando operação..."):
                                        result = asyncio.run(
                                            st.session_state.quotex_client.buy(
                                                st.session_state.selected_asset,
                                                trade_amount,
                                                direction,
                                                expiry_time
                                            )
                                        )
                                        
                                        if result:
                                            st.success(f"💰 Operação executada: {direction.upper()} - ${trade_amount}")
                                            
                                            # Update history
                                            trade_record = {
                                                'timestamp': datetime.now(),
                                                'asset': st.session_state.selected_asset,
                                                'direction': direction.upper(),
                                                'amount': trade_amount,
                                                'pattern': pattern_type,
                                                'backtest_rate': backtest_result['win_rate'],
                                                'status': 'executed'
                                            }
                                            st.session_state.trades_history.append(trade_record)
                                        else:
                                            st.error("❌ Falha ao executar operação")
                            else:
                                st.warning(f"⚠️ Backtest rejeitado: {backtest_result['win_rate']:.1f}% de acerto (< 60%)")
                        else:
                            st.info("👀 Monitorando... Nenhum padrão detectado ainda.")
                            
                except Exception as e:
                    st.error(f"Erro ao obter dados: {str(e)}")
            else:
                st.info("▶️ Inicie o bot para ver dados em tempo real")
        
        with col2:
            st.subheader("📈 Estatísticas")
            
            # Strategy stats
            stats_df = pd.DataFrame([
                {"Métrica": "Total de Operações", "Valor": st.session_state.strategy_stats['total']},
                {"Métrica": "Vitórias", "Valor": st.session_state.strategy_stats['wins']},
                {"Métrica": "Derrotas", "Valor": st.session_state.strategy_stats['losses']},
                {"Métrica": "Taxa de Acerto", "Valor": f"{win_rate:.1f}%"}
            ])
            
            st.dataframe(stats_df, hide_index=True, use_container_width=True)
            
            # Recent trades
            if st.session_state.trades_history:
                st.subheader("🕐 Operações Recentes")
                recent_trades = st.session_state.trades_history[-5:]  # Last 5 trades
                
                trades_df = pd.DataFrame(recent_trades)
                if not trades_df.empty:
                    trades_df['timestamp'] = trades_df['timestamp'].dt.strftime('%H:%M:%S')
                    st.dataframe(
                        trades_df[['timestamp', 'asset', 'direction', 'amount']],
                        hide_index=True,
                        use_container_width=True
                    )
        
        # Auto-refresh for real-time updates
        if st.session_state.trading_active:
            time.sleep(1)  # Wait 1 second
            st.rerun()

if __name__ == "__main__":
    main()
