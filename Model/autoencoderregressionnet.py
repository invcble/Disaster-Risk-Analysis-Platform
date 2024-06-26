# -*- coding: utf-8 -*-
"""AutoEncoderRegressionNet.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/15dvCqg4H_UuA7ovxURyMGfJiu0VBZKfG
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

import torch
import torch.nn as nn

class Autoencoder(nn.Module):
    def __init__(self, num_features):
        super(Autoencoder, self).__init__()
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(num_features, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),  # Encoded representation
            nn.ReLU()
        )
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, num_features),  # Output size same as input size
            nn.Sigmoid()  # use sigmoid if the input is normalized between 0 and 1
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return encoded, decoded

class RegressionNet(nn.Module):
    def __init__(self):
        super(RegressionNet, self).__init__()
        self.fc1 = nn.Linear(16, 64)  # Input size is the size of the encoded features
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, 1)  # Predicting a single value

    def forward(self, x):
        x = self.relu(self.fc1(x))
        return self.fc2(x)

!pip install openpyxl

# Load the data
file_path = 'outG2V2.xlsx'
data = pd.read_excel(file_path)

data.head()

data = data.drop(columns=['Disaster Group','Disaster Subgroup','Disaster Subgroup','No. Injured'])

categorical_features = [ 'Disaster Subtype', 'Location']
numeric_features = ['Start Year']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), numeric_features),
        ('cat', OneHotEncoder(), categorical_features)
    ])

X = preprocessor.fit_transform(data)
y = data['Total Damage, Adjusted (\'000 US$)'].values.reshape(-1, 1)
y = StandardScaler().fit_transform(y)  # Normalize target variable

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Assuming you have already imported the necessary libraries and initialized your data transformations

# After preprocessing with ColumnTransformer, which might output a sparse matrix:
X = preprocessor.fit_transform(data).toarray()  # Convert sparse matrix to dense

# Now, convert these to PyTorch tensors
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

X_train = torch.tensor(X_train.astype(np.float32))
X_test = torch.tensor(X_test.astype(np.float32))
y_train = torch.tensor(y_train.astype(np.float32))
y_test = torch.tensor(y_test.astype(np.float32))


# Create DataLoader
train_data = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_data, batch_size=64, shuffle=True)

autoencoder = Autoencoder(X_train.shape[1])
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(autoencoder.parameters(), lr=0.001)

# Train the autoencoder
num_epochs = 50
for epoch in range(num_epochs):
    for inputs, _ in train_loader:  # No targets needed
        _, decoded = autoencoder(inputs)
        loss = criterion(decoded, inputs)  # Minimize reconstruction loss
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print(f'Epoch {epoch+1}, Loss: {loss.item()}')

# Encode the training data to use as features
encoded_train = []
autoencoder.eval()
with torch.no_grad():
    for inputs, _ in train_loader:
        encoded, _ = autoencoder(inputs)
        encoded_train.append(encoded)
encoded_train = torch.cat(encoded_train, 0)

# Preparing targets to match the encoded features
# Assuming y_train was prepared previously and split accordingly
targets_train = y_train  # This should already be a tensor or converted to tensor if not

# Now, create the TensorDataset with encoded inputs and original targets
encoded_train_data = TensorDataset(encoded_train, targets_train)
encoded_train_loader = DataLoader(encoded_train_data, batch_size=64, shuffle=True)

# Initialize regression model, loss, and optimizer
regression_model = RegressionNet()
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(regression_model.parameters(), lr=0.001)
num_epochs = 100

import torch

for epoch in range(num_epochs):
    regression_model.train()
    total_loss = 0
    for inputs, targets in encoded_train_loader:
        optimizer.zero_grad()
        outputs = regression_model(inputs)
        loss = criterion(outputs, targets)  # MSE
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    average_loss = total_loss / len(encoded_train_loader)
    average_rmse = torch.sqrt(torch.tensor(average_loss))  # RMSE
    print(f'Epoch {epoch+1}, Average MSE: {average_loss}, Average RMSE: {average_rmse}')

def predict_damage(input_data):
    # Assume input_data is a dictionary with the required features
    df = pd.DataFrame([input_data])

    # Preprocessing
    X = preprocessor.transform(df).toarray()  # Using the same preprocessor as during training
    X_tensor = torch.tensor(X.astype(np.float32))  # Convert to tensor

    # Encode the features using the trained autoencoder
    autoencoder.eval()
    with torch.no_grad():
        encoded_features, _ = autoencoder(X_tensor)

    # Predict using the regression model
    regression_model.eval()
    with torch.no_grad():
        predicted_damage = regression_model(encoded_features)

    if predicted_damage.item()< 0:
      return int(-predicted_damage.item()*1e7)
    return predicted_damage.item()

# Example of how to use this function:
input_features = {
    'Start Year': 2021,
    'Disaster Subtype': 'Flood',
    'Location': 'Texas'
}
predicted_damage = predict_damage(input_features)
print(f"Predicted Total Damage: {predicted_damage} '000 US$")

torch.save(autoencoder.state_dict(), 'autoencoder_weights.pth')
torch.save(regression_model.state_dict(), 'regression_model_weights.pth')

!pip install joblib

from joblib import dump

# Save the preprocessor to a file
dump(preprocessor, 'preprocessor.joblib')