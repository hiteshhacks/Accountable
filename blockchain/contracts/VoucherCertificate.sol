// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract VoucherCertificate {

    struct Certificate {
        string certificateNumber;
        bytes32 voucherHash;
        uint256 timestamp;
        bool exists;
    }

    mapping(string => Certificate) private certificates;

    event VoucherCertified(
        string certificateNumber,
        bytes32 voucherHash,
        uint256 timestamp
    );

    function certifyVoucher(
        string calldata certificateNumber,
        bytes32 voucherHash
    ) external {

        require(
            !certificates[certificateNumber].exists,
            "Certificate already exists"
        );

        certificates[certificateNumber] = Certificate({
            certificateNumber: certificateNumber,
            voucherHash: voucherHash,
            timestamp: block.timestamp,
            exists: true
        });

        emit VoucherCertified(
            certificateNumber,
            voucherHash,
            block.timestamp
        );
    }

    function getCertificate(
        string calldata certificateNumber
    )
        external
        view
        returns (
            string memory,
            bytes32,
            uint256,
            bool
        )
    {
        Certificate memory certificate =
            certificates[certificateNumber];

        return (
            certificate.certificateNumber,
            certificate.voucherHash,
            certificate.timestamp,
            certificate.exists
        );
    }
}