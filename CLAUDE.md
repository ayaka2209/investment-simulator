
## スキルのルーティング

ユーザーのリクエストが利用可能なスキルに合致する場合、Skillツールを使って呼び出してください。
スキルには専用のワークフロー・チェックリスト・品質ゲートがあり、場当たり的な回答より良い結果を出します。
迷ったらスキルを呼び出してください。誤検知より見逃しのほうがコストが高いです。

主なルーティングルール:
- プロダクトのアイデア、「これ作る価値ある？」、ブレスト → /office-hours
- 戦略、スコープ、「もっと大きく考えて」、「何を作るべきか」 → /plan-ceo-review
- アーキテクチャ、「この設計で大丈夫？」 → /plan-eng-review
- デザインシステム、ブランド、「どう見せるべき？」 → /design-consultation
- プランのデザインレビュー → /plan-design-review
- プランの開発者体験レビュー → /plan-devex-review
- 「全部レビューして」、フルレビューパイプライン → /autoplan
- バグ、エラー、「なんで壊れてるの」、「動かない」 → /investigate
- サイトのテスト、バグ探し、「ちゃんと動く？」 → /qa（レポートだけなら /qa-only）
- コードレビュー、「差分見て」 → /review
- ビジュアルの改善、デザイン監査、「見た目がおかしい」 → /design-review
- 開発者体験の監査、オンボーディング確認 → /devex-review
- リリース、デプロイ、PR作成、「送って」 → /ship
- マージ＋デプロイ＋確認 → /land-and-deploy
- デプロイ設定 → /setup-deploy
- デプロイ後の監視 → /canary
- リリース後のドキュメント更新 → /document-release
- 週次振り返り、「今週どうだった？」 → /retro
- セカンドオピニオン、別視点のレビュー → /codex
- 安全モード、慎重モード → /careful または /guard
- ディレクトリへの編集を制限 → /freeze または /unfreeze
- gstackのアップグレード → /gstack-upgrade
- 進捗の保存、「作業を保存して」 → /context-save
- 再開、「どこまでやってたっけ」 → /context-restore
- セキュリティ監査、OWASP → /cso
- PDF・ドキュメント作成 → /make-pdf
- QA用にブラウザを起動 → /open-gstack-browser
- 認証済みテスト用クッキーのインポート → /setup-browser-cookies
- パフォーマンス計測 → /benchmark
- gstackの学習内容を確認 → /learn
- 質問の感度チューニング → /plan-tune
- コード品質ダッシュボード → /health
