### Example Ansible playbooks ###

Here are some example playbooks for using the [Insights for RHEL Planning API] to get RHEL lifecycle data. They make the process of getting an access token and using that to interact with Red Hat APIs a bit easier.


#### Prerequisites ####

[Ansible Core] 2.16 or later.

Create a [Red Hat account] and an [offline token]. The offline token is used to generate an access token, which expires in 15 minutes.

#### Running the playbooks ####

Once you have an offline token, set the token to the `RH_OFFLINE_TOKEN` environment variable and run the playbook.


```shell
export RH_OFFLINE_TOKEN=[token]
ansible-playbook rhel-lifecycle-data.yml
```

By default, the response is only display and not saved. To save the response, set `SAVE_RESPONSE=yes`.


### Further Resources ###

See [Getting started with Red Hat APIs] and the [Red Hat API catalog documentation] for more details.

[Insights for RHEL Planning API]: https://developers.redhat.com/api-catalog/api/roadmap
[Ansible Core]: https://pypi.org/project/ansible-core/
[Red Hat account]: https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/registrations?client_id=customer-portal&response_type=code&redirect_uri=https://access.redhat.com
[offline token]: https://access.redhat.com/management/api
[Getting started with Red Hat APIs]: https://access.redhat.com/articles/3626371
[Red Hat API catalog documentation]: https://developers.redhat.com/api-catalog/
