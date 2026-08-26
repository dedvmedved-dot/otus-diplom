# TASK-012-R5-R2 — result

TASK: TASK-012-R5-R2-FIX-ETCD-MEMBER-COUNT-SEMANTICS
RUN_ID: 20260826T174711Z

## Итог
Static-only корректировка. Заменён некорректный textual member count на JSON-aware
member parser в Recovery etcd block.

## Дефект
`grep -c '"ID"'` считал количество СТРОК с pattern, а не members. JSON может быть
одной строкой — тогда 3 members давали бы matching lines = 1 (false FAIL).

## Исправление
JSON-aware parser (python3 json):
- member_count = len(member_list_json["members"])
- member_learner_count = count(isLearner == true)
- fail-closed: exit 2 если members не list, exit 3 если member без "ID"

Ключевое уточнение (фактический etcd 3.6.8): member list -w json использует
omitempty для isLearner — у не-learner поле отсутствует. Parser трактует
отсутствие как non-learner (валидировано Case E unit test), а не как ошибку;
fail-closed срабатывает только на malformed structure.

## Unit tests
4/4 обязательных PASS (A/B/C/D) + Case E (реальный omitempty формат) PASS.

## Read-only verification
members=3, member learners=0, healthy=3, endpoint learners=0, unique leader IDs=1,
actual leader endpoint count=1, leader node-01 (14296685853265834734).
Кластер: 3/3 control-plane, kube-vip 3/3, VIP single-owner node-02, API 3/3,
readyz ok, P1/P2 preserved, CNI absent.

## Статус
Не имеет права присваивать статусы. Присваивает только Главный Архитектор после
независимого GitHub Connector audit.
