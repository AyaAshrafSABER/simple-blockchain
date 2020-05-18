class BlockchainException(Exception):

    def __init__(self, index, message):
        super(BlockchainException, self).__init__(message)
        self.index = index

class InvalidHash(BlockchainException):
    pass

class InvalidTransactions(BlockchainException):
    pass
