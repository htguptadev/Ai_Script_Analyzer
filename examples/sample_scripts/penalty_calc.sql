-- Subroutine to compute penalties
INPUT ACCOUNT_ID
OUTPUT PENALTY_AMOUNT
/* error condition */
IF ACCOUNT_STATUS = 'CLOSED' THEN
    RAISE ERROR 'Closed account'
END IF
