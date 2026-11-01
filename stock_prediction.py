import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error


# Function to create sequences for LSTM model
def create_sequences(data, time_step=90):
    X, Y = [], []
    for i in range(len(data) - time_step):
        X.append(data[i:(i + time_step), 0])
        Y.append(data[i + time_step, 0])
    return np.array(X), np.array(Y)


@st.cache_data(ttl=3600, max_entries=8, show_spinner="Training the stock prediction model...")
def generate_predictions(close_values):
    import tensorflow as tf
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import RMSprop

    time_step = 69
    close_prices = np.asarray(close_values, dtype=np.float64).reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(close_prices)
    X, Y = create_sequences(scaled_data, time_step)
    if len(X) < 10:
        raise ValueError("There is not enough daily price history to train the prediction model.")

    X = X.reshape(X.shape[0], X.shape[1], 1)
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    Y_train, Y_test = Y[:train_size], Y[train_size:]
    if not len(X_train) or not len(X_test):
        raise ValueError("There is not enough daily price history to train and evaluate the model.")

    model = tf.keras.Sequential([
        Input(shape=(time_step, 1)),
        LSTM(32, return_sequences=True),
        Dropout(0.2),
        LSTM(16, return_sequences=False),
        Dropout(0.2),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(
        optimizer=RMSprop(learning_rate=0.001),
        loss="mean_squared_error",
    )
    callbacks = [
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, verbose=0),
        EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
    ]
    model.fit(
        X_train,
        Y_train,
        epochs=30,
        batch_size=32,
        verbose=0,
        validation_data=(X_test, Y_test),
        callbacks=callbacks,
    )

    test_predictions = scaler.inverse_transform(model.predict(X_test, verbose=0))
    actual_prices = scaler.inverse_transform(Y_test.reshape(-1, 1))
    mse = mean_squared_error(actual_prices, test_predictions)
    mae = mean_absolute_error(actual_prices, test_predictions)

    future_values = scaled_data[-time_step:].reshape(1, time_step, 1)
    future_predictions = []
    for _ in range(15):
        prediction = float(model(future_values, training=False).numpy()[0, 0])
        future_predictions.append(prediction)
        future_values = np.concatenate(
            (future_values[:, 1:, :], np.array([[[prediction]]])), axis=1
        )
    future_predictions = scaler.inverse_transform(
        np.asarray(future_predictions).reshape(-1, 1)
    ).flatten()

    return test_predictions.flatten(), future_predictions, mse, mae


# Stock Price Prediction Page
def show_stock_prediction(selected_stock, df):
    st.markdown("## 🤖 Stock Price Prediction (Future Trend)")

    if df.empty:
        st.error("⚠ No data available for this stock.")
        return

    source = df.attrs.get("source", "stock history provider")
    st.caption(f"Price data source: {source}")
    if source.startswith("Google Finance"):
        st.warning(
            "Yahoo Finance was unavailable. The Google Finance backup provides daily "
            "prices for about one month."
        )

    time_step = 69
    if len(df) < time_step + 10:
        st.error(
            "There is not enough daily price history to train the prediction model. "
            "At least 79 trading days are needed."
        )
        return
    try:
        test_predictions, future_predictions, mse, mae = generate_predictions(
            tuple(df["Close"].astype(float))
        )
    except ValueError as error:
        st.error(str(error))
        return

    # Create Date Index for Future
    future_dates = pd.bdate_range(start=df.index[-1] + pd.Timedelta(days=1), periods=15)

    # Plot Predictions
    fig = go.Figure()

    # Actual Prices (Past)
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Actual Price", line=dict(color="blue", width=1.5)))

    # Test Predictions (Past)
    test_dates = df.index[-len(test_predictions):]
    fig.add_trace(go.Scatter(x=test_dates, y=test_predictions, mode="lines", name="Predicted Past Price", line=dict(color="orange", width=1.5)))

    # Future Predictions (Trend)
    fig.add_trace(go.Scatter(x=future_dates, y=future_predictions, mode="lines", name="Predicted Future Price", line=dict(color="red", width=2)))

    # Chart Settings
    fig.update_layout(
        title=f"{selected_stock} Stock Price Prediction",
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        template="plotly_dark",
        hovermode="x"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show Predicted Values
    st.subheader("📜 Future Predicted Prices")
    future_df = pd.DataFrame({"Date": future_dates, "Predicted Price": future_predictions})
    st.dataframe(future_df)

    # Model Evaluation
    st.subheader("📊 Model Evaluation")
    st.write(f"✅ **Mean Squared Error (MSE):** {mse:.4f}")
    st.write(f"✅ **Mean Absolute Error (MAE):** {mae:.4f}")
