from dataclasses import dataclass
from enum import Enum
from typing import Optional

import grpc.aio

from kessel.inventory.v1beta2 import allowed_pb2
from kessel.inventory.v1beta2 import check_request_pb2
from kessel.inventory.v1beta2 import inventory_service_pb2_grpc
from kessel.inventory.v1beta2 import reporter_reference_pb2
from kessel.inventory.v1beta2 import representation_type_pb2
from kessel.inventory.v1beta2 import request_pagination_pb2
from kessel.inventory.v1beta2 import resource_reference_pb2
from kessel.inventory.v1beta2 import streamed_list_objects_request_pb2
from kessel.inventory.v1beta2 import subject_reference_pb2


class Allowed(Enum):
    UNSPECIFIED = 0
    TRUE = 1
    FALSE = 2


@dataclass
class ObjectType:
    resource_type: str
    reporter_type: str

    @staticmethod
    def workspace():
        return ObjectType(
            resource_type="workspace",
            reporter_type="rbac",
        )

    @staticmethod
    def role():
        return ObjectType(resource_type="role", reporter_type="rbac")


@dataclass
class Resource(ObjectType):
    resource_id: str

    @staticmethod
    def principal(resource_id: str):
        return Resource(
            resource_id=resource_id,
            resource_type="principal",
            reporter_type="rbac",
        )

    @staticmethod
    def role(resource_id: str):
        return Resource(
            resource_id=resource_id,
            resource_type="role",
            reporter_type="rbac",
        )

    @staticmethod
    def workspace(resource_id: str):
        return Resource(resource_id=resource_id, resource_type="workspace", reporter_type="rbac")


class KesselClient:
    def __init__(self, host):
        # It is recommended [1] that both channel and stub are re-used.
        # [1] https://grpc.io/docs/guides/performance/
        self.channel = grpc.aio.insecure_channel(host)
        self.stub = inventory_service_pb2_grpc.KesselInventoryServiceStub(self.channel)

    async def close(self):
        await self.channel.close()

    async def get_resources(
        self, object_type: ObjectType, relation: str, subject: Resource, limit: Optional[int] = None, fetch_all=True
    ):
        response = await self._get_resources_internal(object_type, relation, subject, limit=limit)
        while response is not None:
            continuation_token = None
            for data in response:
                yield data.object
                continuation_token = data.pagination.continuation_token

            response = None
            if fetch_all and continuation_token:
                response = await self._get_resources_internal(
                    object_type, relation, subject, limit=limit, continuation_token=continuation_token
                )

    async def _get_resources_internal(
        self,
        object_type: ObjectType,
        relation: str,
        subject: Resource,
        limit: Optional[int] = None,
        continuation_token: Optional[str] = None,
    ):
        request = streamed_list_objects_request_pb2.StreamedListObjectsRequest(
            object_type=representation_type_pb2.RepresentationType(
                resource_type=object_type.resource_type,
                reporter_type=object_type.reporter_type,
            ),
            relation=relation,
            subject=subject_reference_pb2.SubjectReference(
                resource=resource_reference_pb2.ResourceReference(
                    resource_type=subject.resource_type,
                    resource_id=subject.resource_id,
                    reporter=reporter_reference_pb2.ReporterReference(type=subject.reporter_type),
                ),
            ),
            pagination=request_pagination_pb2.RequestPagination(limit=limit, continuation_token=continuation_token),
        )

        return await self.stub.StreamedListObjects(request)

    async def check(self, resource: Resource, relation: str, subject: Resource) -> Allowed:
        request = check_request_pb2.CheckRequest(
            subject=subject_reference_pb2.SubjectReference(
                resource=resource_reference_pb2.ResourceReference(
                    resource_id=subject.resource_id,
                    resource_type=subject.resource_type,
                    reporter=reporter_reference_pb2.ReporterReference(type=subject.reporter_type),
                )
            ),
            relation=relation,
            object=resource_reference_pb2.ResourceReference(
                resource_id=resource.resource_id,
                resource_type=resource.resource_type,
                reporter=reporter_reference_pb2.ReporterReference(type=resource.reporter_type),
            ),
        )

        response = await self.stub.Check(request)
        if response.allowed is allowed_pb2.ALLOWED_TRUE:
            return Allowed.TRUE
        elif response.allowed is allowed_pb2.ALLOWED_FALSE:
            return Allowed.FALSE

        return Allowed.UNSPECIFIED
