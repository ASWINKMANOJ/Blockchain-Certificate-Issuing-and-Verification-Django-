// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CertificateVerification {
    // Custom errors for gas efficiency and clarity
    error CertificateAlreadyExists(string certificateId);
    error CertificateDoesNotExist(string certificateId);
    error OnlyOwner();
    error OnlyIssuer();
    error InvalidAddress();
    error CertificateAlreadyRevoked(string certificateId);
    error IssuerAlreadyAuthorized(address issuer);
    error IssuerNotAuthorized(address issuer);

    // Certificate record - only hash stored on-chain
    struct CertificateRecord {
        bytes32 dataHash;           // keccak256 hash of certificate data
        uint256 issuedAt;           // Timestamp
        bool isRevoked;             // Revocation status
        uint256 revokedAt;          // Revocation timestamp
        address issuer;             // Address of the issuer
    }

    // Owner of the contract
    address public owner;

    // Mapping: certificateId => CertificateRecord
    mapping(string => CertificateRecord) private certificates;

    // Mapping: issuer address => authorized status
    mapping(address => bool) public authorizedIssuers;

    // Track total certificates
    uint256 public totalCertificates;

    // Events
    event CertificateIssued(
        string indexed certificateId,
        bytes32 dataHash,
        uint256 timestamp,
        address indexed issuer
    );

    event CertificateRevoked(
        string indexed certificateId,
        uint256 timestamp
    );

    event IssuerAuthorized(address indexed issuer);
    event IssuerRevoked(address indexed issuer);
    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    // Modifiers
    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    modifier onlyIssuer() {
        if (!authorizedIssuers[msg.sender]) revert OnlyIssuer();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Authorize an address to issue certificates
     * @param _issuer Address to authorize
     */
    function authorizeIssuer(address _issuer) public onlyOwner {
        if (_issuer == address(0)) revert InvalidAddress();
        if (authorizedIssuers[_issuer]) revert IssuerAlreadyAuthorized(_issuer);
        authorizedIssuers[_issuer] = true;
        emit IssuerAuthorized(_issuer);
    }

    /**
     * @dev Revoke authorization from an issuer
     * @param _issuer Address to revoke
     */
    function revokeIssuer(address _issuer) public onlyOwner {
        if (_issuer == address(0)) revert InvalidAddress();
        if (!authorizedIssuers[_issuer]) revert IssuerNotAuthorized(_issuer);
        authorizedIssuers[_issuer] = false;
        emit IssuerRevoked(_issuer);
    }

    /**
     * @dev Issue a certificate - stores only the keccak256 hash
     * @param _certificateId Unique certificate ID
     * @param _dataHash keccak256 hash of certificate data
     */
    function issueCertificate(
        string memory _certificateId,
        bytes32 _dataHash
    ) public onlyIssuer {
        if (bytes(_certificateId).length == 0) revert("Certificate ID cannot be empty");
        if (_dataHash == bytes32(0)) revert("Data hash cannot be empty");
        if (certificates[_certificateId].issuedAt != 0) revert CertificateAlreadyExists(_certificateId);

        certificates[_certificateId] = CertificateRecord({
            dataHash: _dataHash,
            issuedAt: block.timestamp,
            isRevoked: false,
            revokedAt: 0,
            issuer: msg.sender
        });

        totalCertificates++;
        emit CertificateIssued(_certificateId, _dataHash, block.timestamp, msg.sender);
    }

    /**
     * @dev Revoke a certificate (only owner)
     * @param _certificateId ID of the certificate to revoke
     */
    function revokeCertificate(string memory _certificateId) public onlyOwner {
        CertificateRecord storage cert = certificates[_certificateId];

        if (cert.issuedAt == 0) revert CertificateDoesNotExist(_certificateId);
        if (cert.isRevoked) revert CertificateAlreadyRevoked(_certificateId);

        cert.isRevoked = true;
        cert.revokedAt = block.timestamp;

        emit CertificateRevoked(_certificateId, block.timestamp);
    }

    /**
     * @dev Verify certificate by comparing hash
     * @param _certificateId ID of the certificate
     * @param _dataHash keccak256 hash to verify against
     * @return exists Whether certificate exists on blockchain
     * @return isValid Whether certificate is valid (hash matches AND not revoked)
     * @return issuedAt Timestamp when issued
     * @return issuer Address of the issuer
     */
    function verifyCertificate(
        string memory _certificateId,
        bytes32 _dataHash
    ) public view returns (
        bool exists,
        bool isValid,
        uint256 issuedAt,
        address issuer
    ) {
        CertificateRecord memory cert = certificates[_certificateId];
        exists = cert.issuedAt > 0;

        if (!exists) {
            return (false, false, 0, address(0));
        }

        isValid = (cert.dataHash == _dataHash) && !cert.isRevoked;
        return (cert.issuedAt > 0, isValid, cert.issuedAt, cert.issuer);
    }

    /**
     * @dev Quick verify - only check if certificate is valid (exists and not revoked)
     * @param _certificateId ID of the certificate
     * @return isValid Whether certificate exists and is not revoked
     */
    function quickVerify(string memory _certificateId) public view returns (bool isValid) {
        CertificateRecord memory cert = certificates[_certificateId];
        return (cert.issuedAt > 0 && !cert.isRevoked);
    }

    /**
     * @dev Get certificate status and hash
     * @param _certificateId ID of the certificate
     */
    function getCertificateStatus(string memory _certificateId)
        public
        view
        returns (
            bool exists,
            bytes32 dataHash,
            bool isRevoked,
            uint256 issuedAt,
            uint256 revokedAt,
            address issuer
        )
    {
        CertificateRecord memory cert = certificates[_certificateId];
        exists = cert.issuedAt > 0;
        return (
            exists,
            cert.dataHash,
            cert.isRevoked,
            cert.issuedAt,
            cert.revokedAt,
            cert.issuer
        );
    }

    /**
     * @dev Check if certificate exists
     * @param _certificateId ID of the certificate
     */
    function certificateExists(string memory _certificateId) public view returns (bool) {
        return certificates[_certificateId].issuedAt > 0;
    }

    /**
     * @dev Get total number of certificates issued
     */
    function getTotalCertificates() public view returns (uint256) {
        return totalCertificates;
    }

    /**
     * @dev Transfer ownership
     * @param newOwner Address of new owner
     */
    function transferOwnership(address newOwner) public onlyOwner {
        if (newOwner == address(0)) revert InvalidAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
}
