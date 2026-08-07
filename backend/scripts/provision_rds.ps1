$ErrorActionPreference = "Continue"
$Profile = "aws"
$Region = "ap-south-1"

Write-Host "1. Finding default VPC..."
$VpcId = aws ec2 describe-vpcs --profile $Profile --region $Region --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text
Write-Host "Default VPC: $VpcId"

Write-Host "2. Checking for existing security group..."
$SgId = aws ec2 describe-security-groups --profile $Profile --region $Region --group-names "cited-or-silent-sg" --query "SecurityGroups[0].GroupId" --output text 2>$null

if (-not $SgId) {
    Write-Host "Creating new security group..."
    $SgId = aws ec2 create-security-group --profile $Profile --region $Region --group-name "cited-or-silent-sg" --description "Allow 5432 and 6379" --vpc-id $VpcId --query "GroupId" --output text
    
    Write-Host "Adding inbound rules to $SgId..."
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $SgId --protocol tcp --port 5432 --cidr 0.0.0.0/0 | Out-Null
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $SgId --protocol tcp --port 6379 --cidr 0.0.0.0/0 | Out-Null
} else {
    Write-Host "Using existing security group: $SgId"
}

Write-Host "3. Creating RDS PostgreSQL Instance (this will take a few minutes)..."
aws rds create-db-instance `
    --profile $Profile `
    --region $Region `
    --db-instance-identifier cited-or-silent-db `
    --db-instance-class db.t3.micro `
    --engine postgres `
    --engine-version 16 `
    --master-username postgres `
    --master-user-password changeme `
    --allocated-storage 20 `
    --publicly-accessible `
    --vpc-security-group-ids $SgId `
    --no-cli-pager

Write-Host "RDS instance creation triggered. Waiting for it to become available to fetch the endpoint..."
aws rds wait db-instance-available --profile $Profile --region $Region --db-instance-identifier cited-or-silent-db

Write-Host "Fetching endpoint..."
$Endpoint = aws rds describe-db-instances --profile $Profile --region $Region --db-instance-identifier cited-or-silent-db --query "DBInstances[0].Endpoint.Address" --output text

Write-Host "RDS Endpoint is: $Endpoint"
Write-Host "Done!"
