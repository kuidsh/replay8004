# Renew the replay8004-deployer MFA session (12 h) in ~/.aws/credentials. Prints no keys.
# First time, pass the MFA device ARN once; it is saved (not a secret):
#   .\scripts\renew-mfa.ps1 123456 arn:aws:iam::<account>:mfa/<device-name>
# Every time after that:
#   .\scripts\renew-mfa.ps1 123456
param([Parameter(Mandatory = $true)][string]$Code, [string]$Serial)

if ($Serial) { aws configure set mfa_serial $Serial --profile replay8004-deployer }
$serial = aws configure get mfa_serial --profile replay8004-deployer
if (-not $serial) {
    Write-Error "No MFA device saved yet. Run once as: .\scripts\renew-mfa.ps1 <code> arn:aws:iam::<account>:mfa/<device-name>  (IAM > Users > replay8004-deployer > Security credentials > MFA > Identifier)"
    exit 1
}
$c = aws sts get-session-token --profile replay8004-deployer --serial-number $serial --token-code $Code `
    --duration-seconds 43200 --query Credentials --output json | ConvertFrom-Json
if (-not $c) { Write-Error "Renewal failed (wrong or expired code?)."; exit 1 }

aws configure set aws_access_key_id     $c.AccessKeyId     --profile replay8004-deployer-mfa
aws configure set aws_secret_access_key $c.SecretAccessKey --profile replay8004-deployer-mfa
aws configure set aws_session_token     $c.SessionToken    --profile replay8004-deployer-mfa
"Renewed. Expires: $($c.Expiration)"
aws sts get-caller-identity --profile replay8004-deployer-mfa --query Arn --output text
Remove-Variable c
