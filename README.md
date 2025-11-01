# Blockchain Certificate Issuing and Verification System

This project is a decentralized application (DApp) built with Django and Ethereum blockchain for issuing and verifying academic certificates. It provides a secure and transparent way to manage educational certificates using blockchain technology.

## Features

- Secure certificate issuance using blockchain
- Certificate verification system
- Role-based access control (Owner, Organization)
- Certificate revocation capability
- User-friendly dashboard interfaces
- Blockchain-backed authenticity verification

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or higher
- Node.js and npm
- Ganache (GUI version)
- Truffle Framework
- MetaMask browser extension
- Git

## Project Setup

### 1. Clone the Repository
```bash
git clone https://github.com/ASWINKMANOJ/Blockchain-Certificate-Issuing-and-Verification-Django-.git
cd Blockchain-Certificate-Issuing-and-Verification-Django-
```

### 2. Set Up Python Environment
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Smart Contract Deployment

#### Setting up Ganache:
1. Download and install Ganache GUI from [Truffle Suite website](https://trufflesuite.com/ganache/)
2. Launch Ganache and create a new workspace
3. Click on "NEW WORKSPACE"
4. Name your workspace (e.g., "CertificateVerification")
5. In the workspace settings:
   - Set port number to 7545
   - Set Network ID to 5777
   - Enable Automine
6. Save and start the workspace

#### Deploy Smart Contract:
1. Navigate to the contract directory:
```bash
cd contract
```

2. Install Truffle dependencies:
```bash
npm install
```

3. Configure MetaMask:
- Open MetaMask
- Add a new network with the following details:
  - Network Name: Ganache
  - New RPC URL: http://127.0.0.1:7545
  - Chain ID: 5777
  - Currency Symbol: ETH
- Import an account from Ganache using the private key

4. Deploy the smart contract:
```bash
# Compile the smart contract
truffle compile

# Deploy to Ganache
truffle migrate --reset
```

5. Note down the contract address after deployment

### 5. Configure Django Settings

1. Update blockchain settings in `authentication/blockchain.py`:
- Replace the contract address with your deployed contract address
- Update the provider URL if different from default (http://127.0.0.1:7545)

2. Create a superuser for Django admin:
```bash
python manage.py createsuperuser
```

### 6. Run the Application
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000`

## Usage Guide

### Owner Role
- Access the admin panel at `/admin`
- Authorize organizations to issue certificates
- Manage system-wide settings

### Organization Role
- Register using the registration form
- Wait for owner authorization
- Issue new certificates
- View and manage issued certificates
- Revoke certificates if needed

### Certificate Verification
- Anyone can verify certificates using the verification page
- Enter certificate ID to verify authenticity
- View certificate details and verification status

## Smart Contract Details

The `CertificateVerification` smart contract includes:
- Certificate issuance functionality
- Verification methods
- Revocation capability
- Organization management

## Security Features

- Private key management for organizations
- Blockchain-based immutable records
- Role-based access control
- Secure certificate revocation system

## Troubleshooting

1. **Ganache Connection Issues**
   - Ensure Ganache is running
   - Verify network configuration in MetaMask
   - Check RPC URL and port settings

2. **Smart Contract Deployment Failures**
   - Ensure sufficient ETH in deploying account
   - Verify Truffle configuration
   - Check Ganache workspace status

3. **Django Database Issues**
   - Delete db.sqlite3 and migrations
   - Run makemigrations and migrate again
   - Recreate superuser if needed

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.