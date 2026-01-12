Week 1-2: Feature Development
• Squad A: Works in feature/squad-a-checkout ® Deploys to squad-a-dev
• Squad B: Works in feature/squad-b-payment ® Deploys to squad-b-dev
• Squad C: Works in feature/squad-c-refund ® Deploys to squad-c-dev
• Result: Zero conflicts, parallel development, isolated testing
Week 2 End: Merge to Development
• n Squad A: Feature ready ® PR to Development ® Merged
• n Squad C: Feature ready ® PR to Development ® Merged
• nn Squad B: Not ready ® Stays in feature branch
• Development branch = Squad A + Squad C only
Week 3: Release to Test
• Create release/v1.0.0 from Development
• Deploy to Test AWS Account ® Tag: v1.0.0rc1
• QA validates Squad A + C features
• Squad B continues development in parallel (not blocked)
Week 4: Production Deployment
• Merge release/v1.0.0 to Main
• Deploy to Production ® Tag: v1.0.0
• Squad A + C features go live
• Squad B targets next release (v1.1.0)



8. AWS Architecture Integration
The Git Flow strategy integrates seamlessly with AWS Lambda versioning and API Gateway stages:
Git Branch Deployment Target Lambda Alias API Gateway Stage
feature/squad-a-* Dev Account squad-a-dev ® v47 squad-a-dev
feature/squad-b-* Dev Account squad-b-dev ® v48 squad-b-dev
development Dev Account rlc3dev ® v49 rlc3dev
release/v1.0.0 Test Account test ® v45 test
main (prod) Prod Account prod ® v44 prod


9. Key Changes Required
To implement this strategy in your organization, the following changes are necessary:
Infrastructure Changes
3 Create per-squad Lambda aliases in Dev AWS Account
3 Create per-squad API Gateway stages
3 Configure stage variables to route to correct aliases
3 Set up S3 buckets for Lambda package storage per environment
GitHub Configuration
3 Enable branch protection on Development with required status checks
3 Configure JIRA integration for 'Ready for Release' workflow state
3 Set up GitHub Actions workflows for branch-based deployments
3 Create deployment approvals for Test and Prod environments
Team Process Changes
3 Squads maintain feature branches until release-ready
3 Daily rebase practice from Development branch
3 Product Owner approval required before Development merge
3 Release manager creates release branches from Development
CI/CD Pipeline Updates
3 Branch name detection logic for routing deployments
3 Automated Lambda version publishing and alias updates
3 Integration tests per squad environment
3 Rollback automation with CloudWatch alarm integration