## Schema {{ schema.name }}

* Descrição: {{ schema.description }}

{% if schema.tables() %}
### Tabelas

{% for table in schema.tables() %}

#### {{ table.name }}

* Descrição: {{ table.description }}

##### Colunas

{% for column in table.columns() %}
* *{{ column.name }}*

	* Descrição: {{ column.description }}
	* Tipo: {{ column.formatted_type() }}
	* Null? {{ column.formatted_is_nullable() }}
	* Padrão: {{ column.formatted_default() }}

{% endfor %}
{% endfor %}

{% endif %}

{% if schema.views() %}
#### Views

{% for view in schema.views() %}

##### {{ view.name }}

* Descrição: {{ view.description }}

{% endfor %}

{% endif %}