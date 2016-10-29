---
title: Выстраданный результат проекта
output:
   pdf_document:
       toc: true
       highlight: zenburn
   html_document:
       toc: true
       toc_depth: 3
       number_sections: true
       theme: united
       mathjax: null
       css: floating-toc.css 
---

<!--
В блоке YAML выше не должно быть табуляций, только пробелы.

Рендеринг в HTML командой (R, должны быть загружены knitr и rmarkdown):

rmarkdown::render(
   input="Storwize_and_VNX_Performance_Comparision.Rmd", 
   output_format="html_document",encoding="utf8)"
-->

# Краткое содержание для сильно занятых

# Заказчик и идея проекта

Заказчик — московская компания, имеющая большой ассортимент разнообразного
оборудования. Серверы IBM Power и xSeries (как стоечного исполнения, так и
блейды), дисковые массивы HP EVA, HP 3Par и IBM Storwize, а также флэш-массивы
IBM FlashSystem, сетевые устройства Cisco.

Задача — инвентаризировать оборудование, то есть обеспечить понимание, какая машина
где находится и из каких компонентов состоит конкретный сервер.

Идея проекта состоит в том, чтобы основываясь на текущих Open-Source технологиях,
создать для заказчика систему сбора конфигурационных данных.

# Как что устроено <!-- описание решения -->

Решение построено из «кубиков», часть из которых можно заменить для удовлетворения
нужд конкретного заказчика:

  - Аппаратный сервер или виртуальная машина;

  - Linux;

  - СУБД MySQL или PgSQL;

  - Сервер Zabbix 3.x;

  - Интерпретатор и библиотеки Python v3;

  - NoSQL база данных Redis.

Для облегчения себе жизни в качестве базы была взята готовая виртуалка с MySQL
и Zabbix — виртуальная appliance.

# Плюсы-минусы по сравнению с альтернативными решениями

## а какие это альтернативы бывают?

Альтернатив, как показало _подзнейшее_ исследование, оказалось довольно много.
Есть несколько коммерческих продуктов, есть open-source. Список коммерческих
можно посмотреть здесь:
[It Asset Management Comparison)](http://www.softwareadvice.com/help-desk/it-asset-management-comparison).
Большая их часть, насколько мне удалось понять, «заточена» под управление
большим парком персональных машин, серверы были прикручены к решению позднее, а
машины, не имеющие входа в операционную систему и куда нельзя поставить агента,
остались неохваченными.  Зато есть интеграция с Service Desk, можно автоматически
проверять гарантию и довольно много других возможностей. Вообще направление
интересное, стоило бы тут покопаться.

Open-Source решения тоже довольно разнообразны -- от [простого
каталога](http://www.kwoksys.com/wiki/index.php?title=Hardware_Module), куда
информация заносится вручную, через [более продвинутый
каталог](http://www.sivann.gr/software/itdb/). Более интересные решения
предлагают [Snipe-IT] (https://snipeitapp.com/) и [OCS-Inventory
NG](http://www.ocsinventory-ng.org/en/). Последнее вполне можно брать за основу
при проектировании.

## Плюсы

 - Использование успешного OSS продукта Zabbix для хранения конфигурации и показа
   информации пользователям.

 - Способность инвентаризировать, практически, все устройства в локальной сети в полуавтоматическом режиме.
   Для серверов достаточно ввести минимум информации.

 - Нет агентов для установки на инвентаризируемые объекты, обходимся интерфейсами командной
   строки, а также WBEM и IPMI.

## Минусы

 - Использование Jasper Reports для создания отчётов -- сложно и работает с базой данных
   Zabbix напрямую, то есть неустойчиво к изменению внутреннего представления данных в 
   Zabbix.  Нужно переделывать на работу через API Zabbix или использовать для показа
   данных другой продукт.

 - Для инвентаризации любого нового типа объектов необходимо писать код. См.
   раздел [поддерживаемое оборудование и ПО]

# Текущее состояние проекта

## Поддерживаемое оборудование и ПО

 - Дисковые массивы: HP EVA, HP 3Par, IBM DS 4x00, IBM FlashSystem.

 - Серверы: IBM Power (через HMC) под AIX, IBM BladeCenter blades (через AMM) под VMware vSphere,
   IBM xSeries под VMware vSphere.

 - Сетевое оборудование: Cisco (по SMTP).

## Необходимость доработки

Для поддержки любого другого оборудования программы придётся дорабатывать. Во
что это выльется по времени?  Возможны разнообразные варианты: новый тип
дискового массива может быть добавлен за три-пять дней (если у него есть CLI и
она достаточно мощна), кардинально новый тип серверов — задача посложнее, тут
предсказать сроки невозможно. Нужно исследовать вопрос.

# Возможность применения для новых клиентов

Если клиент действительно заинтересован в автоматизированной инвентаризации
своего серверного оборудования, то можно попробовать предложить ему
_адаптировать наше решение под его задачи_. Продукт пока до коробочной стадии
не дошёл, поэтому под каждого клиента понадобится адаптация.  Не обещайте
слишком многого и черезчур быстро.  Пустяковая с точки зрения клиента «фича»
может обернуться месяцем работы, а может быть не реализуема в принципе.

Скорее тут применим принцип гибкой разработки: мы ставим продукт, заказчик
смотрит его и говорит «мне бы такой же, но с перламутровыми пуговицами». Тут
важно сразу бежать к разработчикам и спрашивать, реализуемо ли желание
заказчика в принципе и если да, то в какой срок это можно сделать.  От этого
нужно плясать при разговорах с заказчиком о цене. Если у заказчика появится
следующее пожелание — итерация повторяется.

Договариваться о функциональности на каждой итерации необходимо максимально
конкретно.  Например, в этом проекте заказчик желал "видеть разницу между
текущей конфигурацией и утверждённой".  Вылилось это в "необходимо иметь
возможность получения отчёта о разнице конфигурации любого объекта между
заданной датой и текущей" и из-за этого Жене пришлось прикручивать к решению
Jasper Reports и осваивать синтаксис сложных SQL запросов.

# С кем общаться

Инженеры проекта: [Евгений Ёлкин](mailto:e.elkin@hostco.ru) [Дмитрий Голуб](mailto:d.golub@hostco.ru).
Менеджер проекта [Ольга Попова](mailto:o.popova@hostco.ru)
