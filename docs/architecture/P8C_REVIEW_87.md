# #87 — решение архитектора по листу допуска B

Лист допуска [PR #86](https://git.aiopslab.online/aiopslab/otus-diplom/pulls/86) принят на `bc54184cadfa4228ff0770313c73f3ced7612107`. **Этап B: BLOCKED**, в том числе при `apply_lock=false`. Принят документ, а не решение о публикации или запуске.

## Основания

- Относительно базы `d2f9b39732c19dc8f98ce4e68325b5c6b68fbdcd` PR добавляет только лист допуска. `git diff --check` без замечаний.
- На source `4c09d6b4a85e2d021516244988f48b92eade7acf` независимо выполнено `git ls-tree -r --name-only 4c09d6b4a85e2d021516244988f48b92eade7acf | LC_ALL=C sort | sha256sum`. Результат `e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01` — хеш списка путей, не содержимого. Source и хеш совпали с gate и шаблоном кандидата. [Решение #73](https://git.aiopslab.online/aiopslab/otus-diplom/issues/73) задаёт смену registry; точные значения воспроизведены из git, это не независимое одобрение владельцем запуска на данном SHA.
- Кандидат `32a38ea1223ab8b0e10913a3c32c95d62c2661c6` содержит пять перечисленных в листе файлов и запись `otus-diplom-portal` в корневом `images.lock`, digest `NOT_VERIFIED`. Шаблон соответствует #73: `git.aiopslab.online`, `gitaiopslab`, образ `git.aiopslab.online/aiopslab/otus-diplom-portal` совпадает с source `portal/versions.lock`, три задания используют label `otus-diplom`. Кандидат не закреплён как tools pin; коммиты отчётов не заменяют tools/workflow SHA.

## Передача блокеров

1. **Владелец:** подтвердить в #87 доступность runner с label `otus-diplom` для репозитория и статус `OWNER_GATE`, `REGISTRY_USERNAME`, `REGISTRY_TOKEN`, `POLICY_WORKFLOW_SHA` (последний — после определения точной ревизии workflow). Значения вводить только в Settings → Actions → Secrets. В задаче отвечать по каждому имени «готово» или «ожидает …», без значений и снимков экрана.
2. **Архитектор:** в отдельном наряде на публикацию зафиксировать проверенные `PINNED_TOOLS_SHA` и `FORGEJO_CHECKOUT_SHA` (шесть ссылок checkout); представить точную ревизию workflow владельцу для независимой сверки policy pin. Публикация `.forgejo/workflows/p8c-portal-forgejo-release.yml` не входит в #87.
3. **Решение о запуске:** после подтверждений — отдельное разрешение владельца только на B. Контекст `GITHUB_WORKFLOW_SHA` проверяется в preflight разрешённого запуска; при отсутствии или несовпадении — остановка. C требует отдельного решения по digest и provenance. Исправлений к листу от инженера не требуется.
